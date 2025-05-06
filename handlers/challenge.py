from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, User
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode
from database.connection import (
    get_db_connection, 
    update_user_activity, 
    update_group_activity, 
    update_stats, 
    record_game, 
    record_round,
    add_achievement,
    update_game_winner,
    get_last_moves
)
from datetime import datetime, timedelta
import random
import asyncio

# Game configuration
GAME_CHOICES = {
    "rock": "🪨 Rock", 
    "paper": "📄 Paper", 
    "scissor": "✂️ Scissor"
}
CHOICE_EMOJIS = {
    "rock": "🪨", 
    "paper": "📄", 
    "scissor": "✂️"
}
ongoing_challenges = {}

# Function to clear ongoing challenges
async def clear_ongoing_challenges():
    """Clear all ongoing challenges from memory."""
    global ongoing_challenges
    old_count = len(ongoing_challenges)
    ongoing_challenges.clear()
    return old_count

async def clear_challenges_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id

    count = await clear_user_challenges_in_group(user_id=user_id, chat_id=chat_id)
    await update.message.reply_text(f"🧹 Cleared {count} of your ongoing challenges in this group.")

async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    await update_user_activity(user.id, user.first_name, user.last_name, user.username)
    
    # If in a group, update group activity
    if update.message.chat.type in ["group", "supergroup"]:
        chat = update.message.chat
        await update_group_activity(chat.id, chat.title, chat.username)
    
    # Check if the command is used in a private chat
    if update.message.chat.type == "private":
        await update.message.reply_text("⚠️ This command can only be used in groups.")
        return

    # Check if the command is used as a reply
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to a user's message to challenge them!")
        return

    # Get challenger and challenged users
    challenger = update.message.from_user
    challenged = update.message.reply_to_message.from_user

    # Check if the challenger is trying to challenge themselves
    if challenger.id == challenged.id:
        await update.message.reply_text("😅 You cannot challenge yourself! Find someone else to play with.")
        return

    # Check if the challenged user is a bot
    if challenged.is_bot:
        await update.message.reply_text("🤖 You cannot challenge a bot! Challenge a human player instead.")
        return

    # Update the challenged user's info in DB
    await update_user_activity(challenged.id, challenged.first_name, challenged.last_name, challenged.username)

    # Validate the number of rounds
    try:
        rounds = int(context.args[0]) if context.args else 1
        if not 1 <= rounds <= 10:
            await update.message.reply_text("⚠️ Number of rounds must be between 1-10.")
            return
    except (IndexError, ValueError):
        rounds = 1  # Default to 1 round if not specified

    # Check for existing challenge
    existing_challenge_id = f"{challenger.id}_{challenged.id}"
    if existing_challenge_id in ongoing_challenges:
        await update.message.reply_text(f"⚠️ You already have a pending challenge with {challenged.first_name}!")
        return

    # Create challenge data
    challenge_id = f"{challenger.id}_{challenged.id}"
    ongoing_challenges[challenge_id] = {
        "challenger": challenger,
        "challenged": challenged,
        "rounds": rounds,
        "current_round": 1,
        "challenger_score": 0,
        "challenged_score": 0,
        "status": "pending",
        "chat_id": update.message.chat_id,
        "moves": {
            "challenger": [],
            "challenged": []
        },
        "timestamp": asyncio.get_event_loop().time(),  # For challenge expiry
        "game_id": None  # Will be set when game starts
    }

    # Send challenge message with Accept/Decline buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"accept_{challenge_id}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"decline_{challenge_id}")
        ]
    ]
    
    await update.message.reply_text(
        f"🎮 <b>Game Challenge!</b> 🎮\n\n"
        f"{challenged.first_name}, you've been challenged by {challenger.first_name} "
        f"to a {'multi-round ' if rounds > 1 else ''}game of Rock Paper Scissors!\n\n"
        f"<i>This challenge will expire in 5 minutes</i>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    # Schedule challenge expiry
    context.job_queue.run_once(
        challenge_expiry, 
        300,  # 5 minutes
        data={"challenge_id": challenge_id, "chat_id": update.message.chat_id}
    )

async def challenge_expiry(context: ContextTypes.DEFAULT_TYPE):
    """Handle expiration of challenges that weren't accepted."""
    job_data = context.job.data
    challenge_id = job_data["challenge_id"]
    chat_id = job_data["chat_id"]
    
    if challenge_id in ongoing_challenges and ongoing_challenges[challenge_id]["status"] == "pending":
        challenger = ongoing_challenges[challenge_id]["challenger"]
        challenged = ongoing_challenges[challenge_id]["challenged"]
        
        # Remove the challenge
        del ongoing_challenges[challenge_id]
        
        # Notify about expiration
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⏰ The challenge from {challenger.first_name} to {challenged.first_name} has expired."
        )

# Callback handler for Accept/Decline buttons
async def challenge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    
    # Update user activity
    await update_user_activity(user.id, user.first_name, user.last_name, user.username)
    
    await query.answer()  # Acknowledge the callback

    action, challenge_id = query.data.split("_", 1)
    challenge_data = ongoing_challenges.get(challenge_id)

    if not challenge_data:
        await query.edit_message_text("⚠️ This challenge has expired or was already addressed.")
        return

    # Check if the user responding is the challenged person
    if user.id != challenge_data["challenged"].id:
        await query.answer("This challenge is not for you!", show_alert=True)
        return

    challenger = challenge_data["challenger"]
    challenged = challenge_data["challenged"]

    if action == "decline":
        await query.edit_message_text(
            f"❌ {challenged.first_name} declined the challenge from {challenger.first_name}."
        )
        del ongoing_challenges[challenge_id]
        return
    
    elif action == "accept":
        # Challenge accepted - start the game
        challenge_data["status"] = "active"
        
        # Create the game in the database and get game_id
        game_id = await record_game(
            challenger.id, 
            challenged.id, 
            None,  # winner_id will be set when game ends
            "challenge", 
            challenge_data["rounds"],
            query.message.chat.id
        )
        challenge_data["game_id"] = game_id
        
        await start_challenge(query, challenge_data)

# Start the challenge
async def start_challenge(query, challenge_data):
    challenger = challenge_data["challenger"]
    challenged = challenge_data["challenged"]
    rounds = challenge_data["rounds"]

    # Create a nicely formatted message with emojis and formatting
    message = await query.edit_message_text(
        f"🎮 <b>Game On!</b> 🎮\n\n"
        f"<b>{challenger.first_name}</b> vs <b>{challenged.first_name}</b>\n"
        f"{'🏆 Best of ' + str(rounds) + ' rounds! 🏆' if rounds > 1 else '🏆 Single round battle! 🏆'}\n\n"
        f"<b>Round {challenge_data['current_round']}/{rounds}</b>\n\n"
        f"<b>Score:</b>\n"
        f"{challenger.first_name}: {challenge_data['challenger_score']}\n"
        f"{challenged.first_name}: {challenge_data['challenged_score']}\n\n"
        f"<i>{challenger.first_name}, it's your turn to choose!</i>",
        parse_mode=ParseMode.HTML
    )

    challenge_data["message_id"] = message.message_id
    challenge_data["current_player"] = challenger.id

    await send_move_buttons(query.message.chat.id, challenger)

# Send move buttons in a separate message
async def send_move_buttons(chat_id, player):
    keyboard = [
        [
            InlineKeyboardButton("🪨 Rock", callback_data=f"move_rock_{player.id}"),
            InlineKeyboardButton("📄 Paper", callback_data=f"move_paper_{player.id}"),
            InlineKeyboardButton("✂️ Scissor", callback_data=f"move_scissor_{player.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await player.get_bot().send_message(
        chat_id=chat_id,
        text=f"🎲 <b>{player.first_name}</b>, make your move!\n<i>(Only you can see this message)</i>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

# Determine winner function with more detailed response
def determine_winner(player1_choice, player2_choice):
    """Determine the winner of a round and return formatted result."""
    if player1_choice == player2_choice:
        return "tie", f"Both chose {GAME_CHOICES[player1_choice]}! It's a tie!"
    
    winning_combinations = {
        "rock": "scissor",
        "paper": "rock",
        "scissor": "paper"
    }
    
    if winning_combinations[player1_choice] == player2_choice:
        return "challenger", f"{CHOICE_EMOJIS[player1_choice]} beats {CHOICE_EMOJIS[player2_choice]}!"
    else:
        return "challenged", f"{CHOICE_EMOJIS[player2_choice]} beats {CHOICE_EMOJIS[player1_choice]}!"

# Callback handler for game moves
async def move_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    
    # Update user activity
    await update_user_activity(user.id, user.first_name, user.last_name, user.username)
    
    _, user_choice, user_id = query.data.split("_")
    user_id = int(user_id)

    # Make sure it's this user's turn
    if user.id != user_id:
        await query.answer("It's not your turn!", show_alert=True)
        return
    
    await query.answer()

    # Find the challenge this user is part of
    challenge_id = None
    for cid, data in ongoing_challenges.items():
        if data["status"] == "active" and data["current_player"] == user_id:
            challenge_id = cid
            break
    
    if not challenge_id:
        await query.edit_message_text("This game is no longer active.")
        return

    challenge_data = ongoing_challenges[challenge_id]
    challenger = challenge_data["challenger"]
    challenged = challenge_data["challenged"]
    
    # Store the user's move
    if user.id == challenger.id:
        challenge_data["challenger_move"] = user_choice
        challenge_data["moves"]["challenger"].append(user_choice)
        challenge_data["current_player"] = challenged.id
        
        # Delete the move selection message
        await query.delete_message()
        
        # Update the game status message
        await context.bot.edit_message_text(
            chat_id=challenge_data["chat_id"],
            message_id=challenge_data["message_id"],
            text=f"🎮 <b>Game In Progress</b> 🎮\n\n"
                f"<b>{challenger.first_name}</b> vs <b>{challenged.first_name}</b>\n"
                f"<b>Round {challenge_data['current_round']}/{challenge_data['rounds']}</b>\n\n"
                f"<b>Score:</b>\n"
                f"{challenger.first_name}: {challenge_data['challenger_score']}\n"
                f"{challenged.first_name}: {challenge_data['challenged_score']}\n\n"
                f"✅ {challenger.first_name} has made their move!\n"
                f"<i>{challenged.first_name}, it's your turn now!</i>",
            parse_mode=ParseMode.HTML
        )
        
        # Send move buttons to the challenged player
        await send_move_buttons(challenge_data["chat_id"], challenged)
        
    elif user.id == challenged.id:
        challenge_data["challenged_move"] = user_choice
        challenge_data["moves"]["challenged"].append(user_choice)
        
        # Delete the move selection message
        await query.delete_message()
        
        # Process round results
        challenger_move = challenge_data["challenger_move"]
        challenged_move = user_choice
        
        # Determine winner and explanation
        result, explanation = determine_winner(challenger_move, challenged_move)
        
        # Record the round in the database
        if result == "challenger":
            winner_id = challenger.id
            challenge_data["challenger_score"] += 1
        elif result == "challenged":
            winner_id = challenged.id
            challenge_data["challenged_score"] += 1
        else:  # tie
            winner_id = None
        
        # Record round in database
        await record_round(
            challenge_data["game_id"],
            challenge_data["current_round"],
            challenger_move,
            challenged_move,
            winner_id
        )
        
        # Update player stats with their move choices
        await update_stats(challenger.id, "challenge", "played", challenger_move)
        await update_stats(challenged.id, "challenge", "played", challenged_move)
        
        # Format emoji for moves
        challenger_emoji = CHOICE_EMOJIS[challenger_move]
        challenged_emoji = CHOICE_EMOJIS[challenged_move]
        
        # Update round result message
        round_result_text = (
            f"🎮 <b>Round {challenge_data['current_round']} Result</b> 🎮\n\n"
            f"<b>{challenger.first_name}</b> chose {challenger_emoji} {challenger_move.capitalize()}\n"
            f"<b>{challenged.first_name}</b> chose {challenged_emoji} {challenged_move.capitalize()}\n\n"
            f"{explanation}\n\n"
        )
        
        if result == "challenger":
            round_result_text += f"🏅 <b>{challenger.first_name} wins this round!</b> 🏅"
        elif result == "challenged":
            round_result_text += f"🏅 <b>{challenged.first_name} wins this round!</b> 🏅"
        else:
            round_result_text += "🤝 <b>This round is a tie!</b> 🤝"
        
        await context.bot.edit_message_text(
            chat_id=challenge_data["chat_id"],
            message_id=challenge_data["message_id"],
            text=round_result_text,
            parse_mode=ParseMode.HTML
        )
        
        # Check if game is over
        if challenge_data["current_round"] == challenge_data["rounds"]:
            # Wait 2 seconds before showing final result
            await asyncio.sleep(2)
            await end_game(context, challenge_data)
            return
        
        # Prepare for next round
        challenge_data["current_round"] += 1
        challenge_data["current_player"] = challenger.id
        del challenge_data["challenger_move"]
        del challenge_data["challenged_move"]
        
        # Wait 2 seconds before starting next round
        await asyncio.sleep(2)
        
        # Update message for next round
        await context.bot.edit_message_text(
            chat_id=challenge_data["chat_id"],
            message_id=challenge_data["message_id"],
            text=f"🎮 <b>Game Continues</b> 🎮\n\n"
                f"<b>{challenger.first_name}</b> vs <b>{challenged.first_name}</b>\n"
                f"<b>Round {challenge_data['current_round']}/{challenge_data['rounds']}</b>\n\n"
                f"<b>Score:</b>\n"
                f"{challenger.first_name}: {challenge_data['challenger_score']}\n"
                f"{challenged.first_name}: {challenge_data['challenged_score']}\n\n"
                f"<i>{challenger.first_name}, it's your turn now!</i>",
            parse_mode=ParseMode.HTML
        )
        
        # Send move buttons to challenger
        await send_move_buttons(challenge_data["chat_id"], challenger)

async def end_game(context, challenge_data):
    """End the game and display final results."""
    challenger = challenge_data["challenger"]
    challenged = challenge_data["challenged"]
    challenger_score = challenge_data["challenger_score"]
    challenged_score = challenge_data["challenged_score"]
    game_id = challenge_data["game_id"]
    
    # Determine the overall winner
    if challenger_score > challenged_score:
        winner = challenger
        loser = challenged
        winner_score = challenger_score
        loser_score = challenged_score
        winner_id = challenger.id
        winner_result = "win"
        loser_result = "loss"
    elif challenged_score > challenger_score:
        winner = challenged
        loser = challenger
        winner_score = challenged_score
        loser_score = challenger_score
        winner_id = challenged.id
        winner_result = "win"
        loser_result = "loss"
    else:
        winner = None
        loser = None
        winner_id = None
        winner_result = "tie"
        loser_result = "tie"
    
    # Update game record with the winner
    try:
        await update_game_winner(game_id, winner_id)
    except Exception as e:
        logger.error(f"Error updating game winner for game {game_id}: {e}")
    
    # Get last moves for move streak tracking
    try:
        challenger_move, challenged_move = await get_last_moves(game_id)
    except Exception as e:
        logger.error(f"Error fetching last moves for game {game_id}: {e}")
        challenger_move = None
        challenged_move = None
    
    # Create final result message
    result_text = (
        f"🎮 <b>Game Over!</b> 🎮\n\n"
        f"<b>Final Score:</b>\n"
        f"{challenger.first_name}: {challenger_score}\n"
        f"{challenged.first_name}: {challenged_score}\n\n"
    )
    
    achievement_notifications = []
    
    if winner:
        result_text += (
            f"🏆 <b>{winner.first_name} WINS!</b> 🏆\n"
            f"<i>With a score of {winner_score}-{loser_score}</i>"
        )
        
        # Update stats for both players
        try:
            level_up, new_level = await update_stats(winner.id, "challenge", winner_result, challenger_move if winner.id == challenger.id else challenged_move)
            await update_stats(loser.id, "challenge", loser_result, challenged_move if loser.id == challenged.id else challenger_move)
        except Exception as e:
            logger.error(f"Error updating stats for game {game_id}: {e}")
        
        # Update user progress
        try:
            winner_progress = await update_user_progress(winner.id, winner_result, challenger_move if winner.id == challenger.id else challenged_move)
            loser_progress = await update_user_progress(loser.id, loser_result, challenged_move if loser.id == challenged.id else challenger_move)
        except Exception as e:
            logger.error(f"Error updating user progress for game {game_id}: {e}")
            winner_progress = {'win_streak': 0, 'move_streak': 0}
            loser_progress = {'win_streak': 0, 'move_streak': 0}
        
        # Check achievements for winner
        try:
            existing_achievements = await get_user_achievements(winner.id)
            existing_types = {ach['achievement_type'] for ach in existing_achievements}
            
            # First win
            winner_stats = await get_user_stats(winner.id)
            if winner_stats['total_wins'] == 1 and 'first_win' not in existing_types:
                await add_achievement(winner.id, "first_win", "Won your first challenge game!")
                achievement_notifications.append(f"🎉 <b>Achievement Unlocked for {winner.first_name}:</b> First Win!")
            
            # Perfect victory
            if challenge_data["rounds"] >= 3 and winner_score == challenge_data["rounds"] and 'perfect_victory' not in existing_types:
                await add_achievement(
                    winner.id, 
                    "perfect_victory", 
                    f"Won all {challenge_data['rounds']} rounds against {loser.first_name}"
                )
                achievement_notifications.append(f"🌟 <b>Achievement Unlocked for {winner.first_name}:</b> Perfect Victory!")
            
            # Streak winner
            if winner_progress['win_streak'] >= 3 and 'streak_winner' not in existing_types:
                await add_achievement(winner.id, "streak_winner", "Won 3 games in a row! You're on fire!")
                achievement_notifications.append(f"🔥 <b>Achievement Unlocked for {winner.first_name}:</b> Streak Winner!")
            
            # Move master
            if winner_progress['move_streak'] >= 10 and 'move_master' not in existing_types:
                await add_achievement(winner.id, "move_master", "Mastered a move by playing it 10 times in a row!")
                achievement_notifications.append(f"🎯 <b>Achievement Unlocked for {winner.first_name}:</b> Move Master!")
        except Exception as e:
            logger.error(f"Error checking achievements for winner {winner.id}: {e}")
        
        # Check achievements for loser (only move_master)
        try:
            existing_achievements = await get_user_achievements(loser.id)
            existing_types = {ach['achievement_type'] for ach in existing_achievements}
            
            if loser_progress['move_streak'] >= 10 and 'move_master' not in existing_types:
                await add_achievement(loser.id, "move_master", "Mastered a move by playing it 10 times in a row!")
                achievement_notifications.append(f"🎯 <b>Achievement Unlocked for {loser.first_name}:</b> Move Master!")
        except Exception as e:
            logger.error(f"Error checking achievements for loser {loser.id}: {e}")
        
        # Add level up notification
        if level_up:
            achievement_notifications.append(f"⬆️ <b>{winner.first_name} leveled up to {new_level}!</b> ⬆️")
            
    else:
        result_text += f"🤝 <b>It's a TIE!</b> 🤝"
        
        # Update stats for both players
        try:
            await update_stats(challenger.id, "challenge", "tie", challenger_move)
            await update_stats(challenged.id, "challenge", "tie", challenged_move)
        except Exception as e:
            logger.error(f"Error updating stats for tie game {game_id}: {e}")
        
        # Update user progress
        try:
            challenger_progress = await update_user_progress(challenger.id, "tie", challenger_move)
            challenged_progress = await update_user_progress(challenged.id, "tie", challenged_move)
        except Exception as e:
            logger.error(f"Error updating user progress for tie game {game_id}: {e}")
            challenger_progress = {'win_streak': 0, 'move_streak': 0}
            challenged_progress = {'win_streak': 0, 'move_streak': 0}
        
        # Check achievements for both players (only move_master)
        for player, move, progress in [
            (challenger, challenger_move, challenger_progress),
            (challenged, challenged_move, challenged_progress)
        ]:
            try:
                existing_achievements = await get_user_achievements(player.id)
                existing_types = {ach['achievement_type'] for ach in existing_achievements}
                
                if progress['move_streak'] >= 10 and 'move_master' not in existing_types:
                    await add_achievement(player.id, "move_master", "Mastered a move by playing it 10 times in a row!")
                    achievement_notifications.append(f"🎯 <b>Achievement Unlocked for {player.first_name}:</b> Move Master!")
            except Exception as e:
                logger.error(f"Error checking achievements for player {player.id}: {e}")
    
    # Append achievement notifications
    if achievement_notifications:
        result_text += "\n\n" + "\n".join(achievement_notifications)
    
    # Send final result message
    try:
        await context.bot.edit_message_text(
            chat_id=challenge_data["chat_id"],
            message_id=challenge_data["message_id"],
            text=result_text,
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error sending result message for game {game_id}: {e}")
    
    # Add rematch button
    keyboard = [
        [InlineKeyboardButton("🔄 Rematch", callback_data=f"rematch_{challenger.id}_{challenged.id}")]
    ]
    try:
        await context.bot.send_message(
            chat_id=challenge_data["chat_id"],
            text="Want to play again?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error sending rematch button for game {game_id}: {e}")
    
    # Remove challenge from ongoing list
    challenge_id = f"{challenger.id}_{challenged.id}"
    if challenge_id in ongoing_challenges:
        del ongoing_challenges[challenge_id]

async def handle_rematch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rematch callback query."""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    user = query.from_user
    data = query.data.split('_')
    
    if len(data) != 3 or data[0] != "rematch":
        logger.error(f"Invalid rematch callback data: {query.data}")
        await query.message.reply_text("⚠️ Invalid rematch request.")
        return
    
    try:
        challenger_id = int(data[1])
        challenged_id = int(data[2])
    except ValueError:
        logger.error(f"Invalid user IDs in rematch callback: {query.data}")
        await query.message.reply_text("⚠️ Invalid rematch request.")
        return
    
    # Verify users
    if user.id not in (challenger_id, challenged_id):
        await query.message.reply_text("⚠️ You are not part of this game!")
        return
    
    # Check for ongoing challenges
    challenge_id = f"{challenger_id}_{challenged_id}"
    reverse_challenge_id = f"{challenged_id}_{challenger_id}"
    if challenge_id in ongoing_challenges or reverse_challenge_id in ongoing_challenges:
        await query.message.reply_text("⚠️ A challenge is already ongoing between these players!")
        return
    
    # Determine new challenger and challenged
    if user.id == challenger_id:
        new_challenger_id = challenger_id
        new_challenged_id = challenged_id
    else:
        new_challenger_id = challenged_id
        new_challenged_id = challenger_id
    
    # Start new challenge (reuse existing challenge logic)
    try:
        # Assume start_challenge is a function that initiates a challenge
        # Replace with your actual challenge initiation logic
        challenge_data = {
            "challenger": await context.bot.get_chat_member(chat_id, new_challenger_id).user,
            "challenged": await context.bot.get_chat_member(chat_id, new_challenged_id).user,
            "chat_id": chat_id,
            "rounds": 3,  # Default to best of 3, adjust as needed
            "challenger_score": 0,
            "challenged_score": 0,
            "current_round": 1
        }
        
        # Record new game
        game_id = await record_game(
            player1_id=new_challenger_id,
            player2_id=new_challenged_id,
            winner_id=None,
            game_type="challenge",
            rounds=challenge_data["rounds"],
            group_id=chat_id if query.message.chat.type != "private" else None
        )
        challenge_data["game_id"] = game_id
        
        # Add to ongoing challenges
        ongoing_challenges[f"{new_challenger_id}_{new_challenged_id}"] = challenge_data
        
        # Send challenge request
        keyboard = [
            [InlineKeyboardButton("✅ Accept", callback_data=f"accept_{new_challenger_id}_{new_challenged_id}")],
            [InlineKeyboardButton("❌ Decline", callback_data=f"decline_{new_challenger_id}_{new_challenged_id}")]
        ]
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🔥 <b>Rematch Challenge!</b> 🔥\n"
                f"{challenge_data['challenger'].first_name} challenges {challenge_data['challenged'].first_name} "
                f"to a {challenge_data['rounds']}-round game!\n"
                f"Do you accept?"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        
        # Delete rematch button message
        await query.message.delete()
    except Exception as e:
        logger.error(f"Error starting rematch for users {new_challenger_id} vs {new_challenged_id}: {e}")
        await query.message.reply_text("⚠️ Error starting rematch. Please try again.")


async def update_game_winner(game_id, winner_id):
    """Update the game record with the winner ID."""
    async with get_db_connection() as conn:
        await conn.execute(
            "UPDATE game_history SET winner_id = ? WHERE game_id = ?",
            (winner_id, game_id)
        )
        await conn.commit()

# Handle rematch requests
async def rematch_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, challenger_id, challenged_id = query.data.split("_")
    challenger_id = int(challenger_id)
    challenged_id = int(challenged_id)
    
    # Get user objects
    try:
        challenger = await context.bot.get_chat_member(query.message.chat_id, challenger_id)
        challenged = await context.bot.get_chat_member(query.message.chat_id, challenged_id)
        
        challenger_user = challenger.user
        challenged_user = challenged.user
        
        # Create a new challenge with the same settings as before
        challenge_id = f"{challenger_user.id}_{challenged_user.id}"
        
        ongoing_challenges[challenge_id] = {
            "challenger": challenger_user,
            "challenged": challenged_user,
            "rounds": 3,  # Default to 3 rounds for rematches
            "current_round": 1,
            "challenger_score": 0,
            "challenged_score": 0,
            "status": "pending",
            "chat_id": query.message.chat_id,
            "moves": {
                "challenger": [],
                "challenged": []
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # Send rematch challenge message
        keyboard = [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"accept_{challenge_id}"),
                InlineKeyboardButton("❌ Decline", callback_data=f"decline_{challenge_id}")
            ]
        ]
        
        await query.edit_message_text(
            f"🔄 <b>Rematch Challenge!</b> 🔄\n\n"
            f"{challenged_user.first_name}, {challenger_user.first_name} wants a rematch!\n"
            f"Best of 3 rounds. Do you accept?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
        
        # Schedule challenge expiry
        context.job_queue.run_once(
            challenge_expiry, 
            300,  # 5 minutes
            data={"challenge_id": challenge_id, "chat_id": query.message.chat_id}
        )
        
    except Exception as e:
        print(f"Error in rematch: {e}")
        await query.edit_message_text(
            "Unable to create rematch. Please use /challenge to start a new game."
        )
