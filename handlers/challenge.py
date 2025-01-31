from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import random

# Game choices
GAME_CHOICES = ["🪨 Rock", "📄 Paper", "✂️ Scissor"]

# Dictionary to store ongoing challenges
ongoing_challenges = {}

# Function to determine the winner of a round
def determine_winner(user_choice, bot_choice):
    if user_choice == bot_choice:
        return "tie"
    elif (user_choice == "🪨 Rock" and bot_choice == "✂️ Scissor") or \
         (user_choice == "📄 Paper" and bot_choice == "🪨 Rock") or \
         (user_choice == "✂️ Scissor" and bot_choice == "📄 Paper"):
        return "user"
    else:
        return "bot"

# Command handler for /challenge
async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a user's message to challenge them.")
        return

    try:
        rounds = int(context.args[0]) if context.args else 1
        if rounds < 1 or rounds > 10:
            await update.message.reply_text("Number of rounds must be between 1 and 10.")
            return
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /challenge <rounds> (max 10)")
        return

    challenger = update.message.from_user
    challenged = update.message.reply_to_message.from_user

    if challenger.id == challenged.id:
        await update.message.reply_text("You cannot challenge yourself!")
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
        "status": "pending"
    }

    # Send challenge message with Accept/Decline buttons
    keyboard = [
        [InlineKeyboardButton("✅ Accept", callback_data=f"accept_{challenge_id}")],
        [InlineKeyboardButton("❌ Decline", callback_data=f"decline_{challenge_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"{challenged.first_name}, you have been challenged by {challenger.first_name} for {rounds} round(s)!",
        reply_markup=reply_markup
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

    # Send initial challenge message
    message = await query.edit_message_text(
        f"🎮 {challenger.first_name} vs {challenged.first_name} 🎮\n"
        f"Round 1\n\n"
        f"Score:\n"
        f"{challenger.first_name}: 0\n"
        f"{challenged.first_name}: 0\n\n"
        f"{challenger.first_name}'s turn!"
    )

    # Store the message ID for future updates
    challenge_data["message_id"] = message.message_id
    challenge_data["current_player"] = challenger.id

# Callback handler for game moves
async def move_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_choice = query.data
    user = query.from_user

    # Find the challenge
    challenge_id = None
    for key, data in ongoing_challenges.items():
        if data["current_player"] == user.id:
            challenge_id = key
            break

    if not challenge_id:
        await query.answer("It's not your turn!")
        return

    challenge_data = ongoing_challenges[challenge_id]
    challenger = challenge_data["challenger"]
    challenged = challenge_data["challenged"]

    # Determine the opponent's choice
    opponent_choice = random.choice(GAME_CHOICES)

    # Determine the winner of the round
    result = determine_winner(user_choice, opponent_choice)

    # Update scores
    if result == "user":
        if user.id == challenger.id:
            challenge_data["challenger_score"] += 1
        else:
            challenge_data["challenged_score"] += 1
    elif result == "bot":
        if user.id == challenger.id:
            challenge_data["challenged_score"] += 1
        else:
            challenge_data["challenger_score"] += 1

    # Prepare the result message
    result_message = f"{user.first_name} chose {user_choice}\n"
    result_message += f"{challenged.first_name if user.id == challenger.id else challenger.first_name} chose {opponent_choice}\n\n"
    if result == "tie":
        result_message += "It's a tie! 🤝"
    else:
        result_message += f"{user.first_name if result == 'user' else (challenged.first_name if user.id == challenger.id else challenger.first_name)} wins this round! 🎉"

    # Update the challenge message
    await query.edit_message_text(
        f"🎮 {challenger.first_name} vs {challenged.first_name} 🎮\n"
        f"Round {challenge_data['current_round']}\n\n"
        f"Score:\n"
        f"{challenger.first_name}: {challenge_data['challenger_score']}\n"
        f"{challenged.first_name}: {challenge_data['challenged_score']}\n\n"
        f"{result_message}"
    )

    # Check if all rounds are completed
    if challenge_data["current_round"] == challenge_data["rounds"]:
        # Determine the final winner
        if challenge_data["challenger_score"] > challenge_data["challenged_score"]:
            winner = challenger.first_name
        elif challenge_data["challenger_score"] < challenge_data["challenged_score"]:
            winner = challenged.first_name
        else:
            winner = "It's a tie!"

        await query.edit_message_text(
            f"🎮 {challenger.first_name} vs {challenged.first_name} 🎮\n"
            f"Final Score:\n"
            f"{challenger.first_name}: {challenge_data['challenger_score']}\n"
            f"{challenged.first_name}: {challenge_data['challenged_score']}\n\n"
            f"🏆 {winner} wins the challenge! 🏆"
        )
        del ongoing_challenges[challenge_id]
        return

    # Move to the next round
    challenge_data["current_round"] += 1
    challenge_data["current_player"] = challenged.id if challenge_data["current_player"] == challenger.id else challenger.id

    # Update the message for the next round
    await query.edit_message_text(
        f"🎮 {challenger.first_name} vs {challenged.first_name} 🎮\n"
        f"Round {challenge_data['current_round']}\n\n"
        f"Score:\n"
        f"{challenger.first_name}: {challenge_data['challenger_score']}\n"
        f"{challenged.first_name}: {challenge_data['challenged_score']}\n\n"
        f"{challenger.first_name if challenge_data['current_player'] == challenger.id else challenged.first_name}'s turn!"
    )
