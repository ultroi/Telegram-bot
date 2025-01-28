from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ContextTypes
from .multiplayer import start_multiplayer, join_multiplayer, handle_multiplayer_move, handle_game_end, matchmaking_process
from .show_stats import show_stats
from .help_command import help_command
import random

# Function to determine the bot's move
def determine_bot_move(player_move):
    if player_move == 'rock':
        return 'paper'
    elif player_move == 'paper':
        return 'scissors'
    else:
        return 'rock'

# Handler for the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Single Player", callback_data='single_player')],
        [InlineKeyboardButton("Multiplayer", callback_data='multiplayer')],
        [InlineKeyboardButton("Show Stats", callback_data='show_stats')],
        [InlineKeyboardButton("Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome! Choose an option:", reply_markup=reply_markup)

# Handler for the game moves
async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player_move = update.message.text.lower()
    bot_move = determine_bot_move(player_move)
    await update.message.reply_text(f"You chose {player_move}, I chose {bot_move}.")

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

    player_choice = query.data.split('_')[0]
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    result = determine_winner(player_choice, bot_choice)

    # Placeholder for update_stats function
    # update_stats(query.from_user.id, result)

    keyboard = [
        [InlineKeyboardButton("Play Again 🔄", callback_data='single_player')],
        [InlineKeyboardButton("Check Stats 📊", callback_data='show_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        f"**You chose:** {player_choice} 🪨📄✂️\n"
        f"**Bot chose:** {bot_choice} 🤖\n"
        f"**{result}** 🎉"
    )
    await query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

# Determine the winner of the game
def determine_winner(player_choice, opponent_choice):
    outcomes = {
        'rock': {'rock': 'tie', 'paper': 'loss', 'scissors': 'win'},
        'paper': {'rock': 'win', 'paper': 'tie', 'scissors': 'loss'},
        'scissors': {'rock': 'loss', 'paper': 'win', 'scissors': 'tie'}
    }
    return outcomes[player_choice][opponent_choice]

# Callback query handler
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'single_player':
        await start_single_player(update, context)
    elif query.data in ['rock_bot', 'paper_bot', 'scissors_bot']:
        await single_player_move(update, context)
    elif query.data == 'multiplayer':
        await start_multiplayer(update, context)
    elif query.data == 'show_stats':
        await show_stats(update, context)
    elif query.data == 'help':
        await help_command(update, context)
