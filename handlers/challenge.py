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
    add_achievement
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
    """Challenge another user to a game of Rock Paper Scissors."""
    # Update user and group activity
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
    
    # Determine the overall winner
    if challenger_score > challenged_score:
        winner = challenger
        loser = challenged
        winner_score = challenger_score
        loser_score = challenged_score
        winner_id = challenger.id
    elif challenged_score > challenger_score:
        winner = challenged
        loser = challenger
        winner_score = challenged_score
        loser_score = challenger_score
        winner_id = challenged.id
    else:
        winner = None
        loser = None
        winner_id = None
    
    # Update game record with the winner
    game_id = challenge_data["game_id"]
    await update_game_winner(game_id, winner_id)
    
    # Create final result message
    if winner:
        result_text = (
            f"🎮 <b>Game Over!</b> 🎮\n\n"
            f"<b>Final Score:</b>\n"
            f"{challenger.first_name}: {challenger_score}\n"
            f"{challenged.first_name}: {challenged_score}\n\n"
            f"🏆 <b>{winner.first_name} WINS!</b> 🏆\n"
            f"<i>With a score of {winner_score}-{loser_score}</i>"
        )
        
        # Update stats for both players (only for challenge mode)
        level_up, new_level = await update_stats(winner.id, "challenge", "win")
        await update_stats(loser.id, "challenge", "loss")
        
        # Check for achievements
        if challenge_data["rounds"] >= 3 and winner_score == challenge_data["rounds"]:
            # Perfect victory achievement
            await add_achievement(
                winner.id, 
                "perfect_victory", 
                f"Won all {challenge_data['rounds']} rounds against {loser.first_name}"
            )
            result_text += f"\n\n🌟 <b>Achievement Unlocked:</b> Perfect Victory! 🌟"
        
        # Add level up notification if applicable
        if level_up:
            result_text += f"\n\n⬆️ <b>{winner.first_name} leveled up to {new_level}!</b> ⬆️"
            
    else:
        result_text = (
            f"🎮 <b>Game Over!</b> 🎮\n\n"
            f"<b>Final Score:</b>\n"
            f"{challenger.first_name}: {challenger_score}\n"
            f"{challenged.first_name}: {challenged_score}\n\n"
            f"🤝 <b>It's a TIE!</b> 🤝"
        )
        
        # Update stats for both players (only for challenge mode)
        await update_stats(challenger.id, "challenge", "tie")
        await update_stats(challenged.id, "challenge", "tie")
    
    # Send final result message
    await context.bot.edit_message_text(
        chat_id=challenge_data["chat_id"],
        message_id=challenge_data["message_id"],
        text=result_text,
        parse_mode=ParseMode.HTML
    )
    
    # Add rematch button
    keyboard = [
        [InlineKeyboardButton("🔄 Rematch", callback_data=f"rematch_{challenger.id}_{challenged.id}")]
    ]
    await context.bot.send_message(
        chat_id=challenge_data["chat_id"],
        text="Want to play again?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    # Remove challenge from ongoing list
    challenge_id = f"{challenger.id}_{challenged.id}"
    if challenge_id in ongoing_challenges:
        del ongoing_challenges[challenge_id]

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
