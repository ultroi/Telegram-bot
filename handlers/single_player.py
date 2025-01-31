from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ContextTypes
import random

# Start single-player mode
async def start_single_player(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Rock 🪨", callback_data='rock_bot')],
        [InlineKeyboardButton("Paper 📄", callback_data='paper_bot')],
        [InlineKeyboardButton("Scissors ✂️", callback_data='scissors_bot')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query = update.callback_query
    await query.edit_message_text(text="You are playing against the bot! Choose your move:", reply_markup=reply_markup)

# Handle single-player moves
async def single_player_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Extract player's choice from callback data
    player_choice = query.data.split('_')[0]  # e.g., 'rock_bot' -> 'rock'
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    result = determine_winner(player_choice, bot_choice)

    # Prepare the result message
    message = (
        f"**You chose:** {player_choice} 🪨📄✂️\n"
        f"**Bot chose:** {bot_choice} 🤖\n"
        f"**{result}** 🎉"
    )

    # Add buttons for playing again or checking stats
    keyboard = [
        [InlineKeyboardButton("Play Again 🔄", callback_data='single_player')],
        [InlineKeyboardButton("Check Stats 📊", callback_data='show_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Update the message with the result and new buttons
    await query.edit_message_text(text=message, reply_markup=reply_markup, parse_mode='Markdown')

# Determine the winner of the game
def determine_winner(player_choice, opponent_choice):
    outcomes = {
        'rock': {'rock': 'It\'s a tie!', 'paper': 'You lose!', 'scissors': 'You win!'},
        'paper': {'rock': 'You win!', 'paper': 'It\'s a tie!', 'scissors': 'You lose!'},
        'scissors': {'rock': 'You lose!', 'paper': 'You win!', 'scissors': 'It\'s a tie!'}
    }
    return outcomes[player_choice][opponent_choice]
