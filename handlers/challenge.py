from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import random

# Game choices
GAME_CHOICES = ["🪨 Rock", "📄 Paper", "✂️ Scissor"]

# Dictionary to store ongoing challenges
ongoing_challenges = {}

# Function to determine the winner of a round
def determine_winner(player1_choice, player2_choice):
    if player1_choice == player2_choice:
        return "tie"
    elif (player1_choice == "🪨 Rock" and player2_choice == "✂️ Scissor") or \
         (player1_choice == "📄 Paper" and player2_choice == "🪨 Rock") or \
         (player1_choice == "✂️ Scissor" and player2_choice == "📄 Paper"):
        return "user"  # Challenger wins
    else:
        return "challenged"  # Challenged player wins


async def challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Debug: Print the message and reply_to_message
    print(f"Message: {update.message.text}")
    print(f"Reply to Message: {update.message.reply_to_message}")

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

    # Debug: Print challenger and challenged details
    print(f"Challenger: {challenger.first_name} (ID: {challenger.id})")
    print(f"Challenged: {challenged.first_name} (ID: {challenged.id})")

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

    # Debug: Print ongoing_challenges
    print(f"Ongoing Challenges: {ongoing_challenges}")

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

    # Find the challenge
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

        # Both players have made their moves, determine the winner
        result = determine_winner(challenge_data["challenger_move"], challenge_data["challenged_move"])

        if result == "user":
            challenge_data["challenger_score"] += 1
            round_winner = challenger.first_name
        elif result == "challenged":
            challenge_data["challenged_score"] += 1
            round_winner = challenged.first_name
        else:
            round_winner = "It's a tie!"

        # Update message with round results
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

        # Check if the game is over
        if challenge_data["current_round"] == challenge_data["rounds"]:
            final_winner = (
                challenger.first_name if challenge_data["challenger_score"] > challenge_data["challenged_score"]
                else challenged.first_name if challenge_data["challenger_score"] < challenge_data["challenged_score"]
                else "It's a tie!"
            )

            await query.message.reply_text(
                f"\U0001F3AE {challenger.first_name} vs {challenged.first_name} \U0001F3AE\n"
                f"Final Score:\n"
                f"{challenger.first_name}: {challenge_data['challenger_score']}\n"
                f"{challenged.first_name}: {challenge_data['challenged_score']}\n\n"
                f"\U0001F3C6 {final_winner} wins the challenge! \U0001F3C6"
            )
            del ongoing_challenges[challenge_id]
            return

        # Move to next round
        challenge_data["current_round"] += 1
        challenge_data["current_player"] = challenger.id  # Next round starts with challenger
        del challenge_data["challenger_move"]
        del challenge_data["challenged_move"]
        await query.message.reply_text(f"Round {challenge_data['current_round']}! {challenger.first_name}, it's your turn!")
        await send_move_buttons(query, challenger)
