from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from .multiplayer import start_multiplayer, join_multiplayer, handle_multiplayer_move, handle_game_end, matchmaking_process
from .show_stats import show_stats
from .single_player import start_single_player
from .help_command import help_command

# Function to determine the bot's move
def determine_bot_move(player_move):
    if player_move == 'rock':
        return 'paper'
    elif player_move == 'paper':
        return 'scissors'
    else:
        return 'rock'

# Handler for the /start command
def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("Single Player", callback_data='single_player')],
        [InlineKeyboardButton("Multiplayer", callback_data='multiplayer')],
        [InlineKeyboardButton("Show Stats", callback_data='show_stats')],
        [InlineKeyboardButton("Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Welcome! Choose an option:", reply_markup=reply_markup)

# Handler for the game moves
def handle_move(update: Update, context):
    player_move = update.message.text.lower()
    bot_move = determine_bot_move(player_move)
    update.message.reply_text(f"You chose {player_move}, I chose {bot_move}.")

# Callback query handler
def handle_callback_query(update: Update, context):
    query = update.callback_query
    if query.data == 'single_player':
        start_single_player(update, context)
    elif query.data == 'multiplayer':
        start_multiplayer(update, context)
    elif query.data == 'show_stats':
        show_stats(update, context)
    elif query.data == 'help':
        help_command(update, context)
