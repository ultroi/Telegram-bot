from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from database.connection import get_db_connection, ensure_tables_exist, update_stats
import random

# Game configuration
GAME_CHOICES = ["🪨 Rock", "📄 Paper", "✂️ Scissor"]
ongoing_challenges = {}

# Function to clear ongoing challenges
async def clear_ongoing_challenges():
    """Clear all ongoing challenges from memory."""
    global ongoing_challenges
    ongoing_challenges.clear()
    print("All ongoing challenges have been cleared.")

async def clear_challenges_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to clear all ongoing challenges."""
    # Optional: Restrict this command to admins or specific users
    admin_id = 5956598856
    if update.message.from_user.id != admin_id:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    clear_ongoing_challenges()
    await update.message.reply_text("All ongoing challenges have been cleared.")



async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the command is used in a private chat
    if update.message.chat.type == "private":
        await update.message.reply_text("This command can only be used in groups.")
        return

    # Check if the command is used as a reply
    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a user's message to challenge them.")
        return

    # Get challenger and challenged users
    challenger = update.message.from_user
    challenged = update.message.reply_to_message.from_user

    # Check if the challenger is trying to challenge themselves
    if challenger.id == challenged.id:
        await update.message.reply_text("You cannot challenge yourself!")
        return

    # Check if the challenged user is a bot
    if challenged.is_bot:
        await update.message.reply_text("You cannot challenge a bot!")
        return

    # Validate the number of rounds
    try:
        rounds = int(context.args[0]) if context.args else 1
        if not 1 <= rounds <= 10:
            await update.message.reply_text("Number of rounds must be between 1-10.")
            return
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /challenge <rounds> (max 10)")
        return

    # Save basic info of both users in the database
    async with get_db_connection() as conn:
        # Ensure both users exist in the database
        for user in [challenger, challenged]:
            await conn.execute('''
                INSERT INTO users (user_id, first_name, last_name, username) 
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    username = excluded.username
            ''', (user.id, user.first_name, user.last_name or "", user.username or ""))
        await conn.commit()

    # Create challenge data
    challenge_id = f"{challenger.id}_{challenged.id}"
    ongoing_challenges[challenge_id] = {
        "challenger": challenger,
        "challenged": challenged,
        "rounds": rounds,
        "current_round": 1,
        "challenger_score": 0,
        "challenged_score": 0,
        "status": "pending"
    }

    # Send challenge message with Accept/Decline buttons
    keyboard = [
        [InlineKeyboardButton("✅ Accept", callback_data=f"accept_{challenge_id}")],
        [InlineKeyboardButton("❌ Decline", callback_data=f"decline_{challenge_id}")]
    ]
    await update.message.reply_text(
        f"{challenged.first_name}, you've been challenged by {challenger.first_name} for {rounds} round(s)!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# Callback handler for Accept/Decline buttons
async def challenge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, challenge_id = query.data.split("_")
    challenge_data = ongoing_challenges.get(challenge_id)

    if not challenge_data:
        await query.edit_message_text("Challenge expired or not found.")
        return

    if action == "decline":
        await query.edit_message_text(f"{challenge_data['challenged'].first_name} declined the challenge.")
        del ongoing_challenges[challenge_id]
        return

    # Challenge accepted
    challenge_data["status"] = "accepted"
    await start_challenge(query, challenge_data)

# Start the challenge
async def start_challenge(query, challenge_data):
    challenger = challenge_data["challenger"]
    challenged = challenge_data["challenged"]

    message = await query.edit_message_text(
        f"\U0001F3AE {challenger.first_name} vs {challenged.first_name} \U0001F3AE\n"
        f"Round 1\n\n"
        f"Score:\n"
        f"{challenger.first_name}: 0\n"
        f"{challenged.first_name}: 0\n\n"
        f"{challenger.first_name}'s turn!"
    )

    challenge_data["message_id"] = message.message_id
    challenge_data["current_player"] = challenger.id

    await send_move_buttons(query, challenger)

# Send move buttons
async def send_move_buttons(query, player):
    keyboard = [
        [InlineKeyboardButton("\U0001FAA8 Rock", callback_data=f"move_rock_{player.id}")],
        [InlineKeyboardButton("\U0001F4C4 Paper", callback_data=f"move_paper_{player.id}")],
        [InlineKeyboardButton("\u2702 Scissor", callback_data=f"move_scissor_{player.id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(f"{player.first_name}, choose your move:", reply_markup=reply_markup)

# Determine winner function
def determine_winner(player1_choice, player2_choice):
    if player1_choice == player2_choice:
        return "tie"
    elif (player1_choice == "rock" and player2_choice == "scissor") or \
         (player1_choice == "paper" and player2_choice == "rock") or \
         (player1_choice == "scissor" and player2_choice == "paper"):
        return "user"  # Challenger wins
    else:
        return "challenged"  # Challenged player wins

# Callback handler for game moves
async def move_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, user_choice, user_id = query.data.split("_")
    user_id = int(user_id)
    user = query.from_user

    challenge_id = next((key for key, data in ongoing_challenges.items() if data["current_player"] == user_id), None)
    if not challenge_id:
        await query.answer("It's not your turn!")
        return

    challenge_data = ongoing_challenges[challenge_id]
    challenger = challenge_data["challenger"]
    challenged = challenge_data["challenged"]

    if user.id == challenger.id:
        challenge_data["challenger_move"] = user_choice
        challenge_data["current_player"] = challenged.id
        await query.edit_message_text(f"{challenger.first_name} has made a move! Now it's {challenged.first_name}'s turn.")
        await send_move_buttons(query, challenged)
        return

    elif user.id == challenged.id:
        challenge_data["challenged_move"] = user_choice

        result = determine_winner(challenge_data["challenger_move"], challenge_data["challenged_move"])

        if result == "user":
            challenge_data["challenger_score"] += 1
            round_winner = challenger.first_name
        elif result == "challenged":
            challenge_data["challenged_score"] += 1
            round_winner = challenged.first_name
        else:
            round_winner = "It's a tie!"

        await query.edit_message_text(
            f"\U0001F3AE {challenger.first_name} vs {challenged.first_name} \U0001F3AE\n"
            f"Round {challenge_data['current_round']}\n\n"
            f"Score:\n"
            f"{challenger.first_name}: {challenge_data['challenger_score']}\n"
            f"{challenged.first_name}: {challenge_data['challenged_score']}\n\n"
            f"{challenger.first_name} chose {challenge_data['challenger_move']}\n"
            f"{challenged.first_name} chose {challenge_data['challenged_move']}\n\n"
            f"\U0001F3C6 {round_winner} wins this round! \U0001F3C6"
        )

        if challenge_data["current_round"] == challenge_data["rounds"]:
            challenger_score = challenge_data["challenger_score"]
            challenged_score = challenge_data["challenged_score"]

            if challenger_score > challenged_score:
                winner_user = challenger
                loser_user = challenged
                final_winner_text = f"{winner_user.first_name} wins the challenge!"
            elif challenged_score > challenger_score:
                winner_user = challenged
                loser_user = challenger
                final_winner_text = f"{winner_user.first_name} wins the challenge!"
            else:
                winner_user = None
                loser_user = None
                final_winner_text = "It's a tie!"

            await query.message.reply_text(
                f"\U0001F3AE {challenger.first_name} vs {challenged.first_name} \U0001F3AE\n"
                f"Final Score:\n"
                f"{challenger.first_name}: {challenger_score}\n"
                f"{challenged.first_name}: {challenged_score}\n\n"
                f"\U0001F3C6 {final_winner_text} \U0001F3C6"
            )

            if winner_user and loser_user:
                # Update winner
                winner_profile = f"t.me/{winner_user.username}" if winner_user.username else None
                await update_stats(
                    user_id=str(winner_user.id),
                    first_name=winner_user.first_name,
                    last_name=winner_user.last_name or '',
                    profile_link=winner_profile,
                    result='win',
                    is_challenge=True
                )
                # Update loser
                loser_profile = f"t.me/{loser_user.username}" if loser_user.username else None
                await update_stats(
                    user_id=str(loser_user.id),
                    first_name=loser_user.first_name,
                    last_name=loser_user.last_name or '',
                    profile_link=loser_profile,
                    result='loss',
                    is_challenge=True
                )

            del ongoing_challenges[challenge_id]
            return

        challenge_data["current_round"] += 1
        challenge_data["current_player"] = challenger.id
        del challenge_data["challenger_move"]
        del challenge_data["challenged_move"]
        await query.message.reply_text(f"Round {challenge_data['current_round']}! {challenger.first_name}, it's your turn!")
        await send_move_buttons(query, challenger)
