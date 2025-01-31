from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import random

# Game choices
GAME_CHOICES = ["🪨 Rock", "📄 Paper", "✂️ Scissor"]

# Function to determine the winner
def determine_winner(user_choice, bot_choice):
    if user_choice == bot_choice:
        return "tie"
    elif (user_choice == "🪨 Rock" and bot_choice == "✂️ Scissor") or \
         (user_choice == "📄 Paper" and bot_choice == "🪨 Rock") or \
         (user_choice == "✂️ Scissor" and bot_choice == "📄 Paper"):
        return "user"
    else:
        return "bot"

# Command handler for /play
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Create buttons for Rock, Paper, Scissor
    keyboard = [
        [InlineKeyboardButton("🪨 Rock", callback_data="🪨 Rock")],
        [InlineKeyboardButton("📄 Paper", callback_data="📄 Paper")],
        [InlineKeyboardButton("✂️ Scissor", callback_data="✂️ Scissor")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message with buttons
    await update.message.reply_text("Your Turn ->> Choose your move:", reply_markup=reply_markup)

# Callback handler for button presses
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Get user's choice
    user_choice = query.data

    # Bot's random choice
    bot_choice = random.choice(GAME_CHOICES)

    # Determine the winner
    result = determine_winner(user_choice, bot_choice)

    # Prepare the result message
    if result == "tie":
        result_message = "It's a tie! 🤝"
    elif result == "user":
        result_message = f"{update.callback_query.from_user.first_name} wins! 🎉"
    else:
        result_message = "Bot wins! 🤖"

    # Edit the original message to show the result
    await query.edit_message_text(
        f"Your choice: {user_choice}\n"
        f"Bot's choice: {bot_choice}\n\n"
        f"{result_message}"
    )
