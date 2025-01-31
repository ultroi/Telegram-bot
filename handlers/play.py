from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random
from database.connection import get_db_connection  # Import database connection

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
    """Sends interactive buttons for the user to select Rock, Paper, or Scissors."""
    chat_type = update.message.chat.type  # Check if it's a private chat

    if chat_type != "private":
        await update.message.reply_text("❌ This command can only be used in private chat!")
        return

    
    keyboard = [
        [InlineKeyboardButton("🪨 Rock", callback_data="🪨 Rock")],
        [InlineKeyboardButton("📄 Paper", callback_data="📄 Paper")],
        [InlineKeyboardButton("✂️ Scissor", callback_data="✂️ Scissor")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Your Turn ->> Choose your move:", reply_markup=reply_markup)

# Callback handler for button presses
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the user's game selection and determines the winner."""
    query = update.callback_query
    user = query.from_user  # Get user info
    user_choice = query.data
    bot_choice = random.choice(GAME_CHOICES)
    result = determine_winner(user_choice, bot_choice)

    # Initialize win/loss update variables
    win_update = 0
    loss_update = 0

    # Determine and store the game result
    if result == "tie":
        result_message = "It's a tie! 🤝"
    elif result == "user":
        result_message = f"{user.first_name} wins! 🎉"
        win_update = 1  # Increment win count
    else:
        result_message = "Bot wins! 🤖"
        loss_update = 1  # Increment loss count

    # Update database with game result
    async with get_db_connection() as conn:
        await conn.execute('''
            INSERT INTO stats (user_id, first_name, last_name, profile_link, total_wins, total_losses)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                first_name = excluded.first_name, 
                last_name = excluded.last_name, 
                profile_link = excluded.profile_link,
                total_wins = stats.total_wins + ?, 
                total_losses = stats.total_losses + ?
        ''', (user.id, user.first_name, user.last_name or '', f"tg://user?id={user.id}", win_update, loss_update, win_update, loss_update))
        await conn.commit()

    # Edit message to display the result
    await query.edit_message_text(
        f"Your choice: {user_choice}\n"
        f"Bot's choice: {bot_choice}\n\n"
        f"{result_message}"
    )
