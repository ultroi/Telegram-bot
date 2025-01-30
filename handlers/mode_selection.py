from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ContextTypes
from .multiplayer import start_multiplayer, join_multiplayer, handle_multiplayer_move, handle_game_end, matchmaking_process
from .show_stats import show_stats
from .single_player import start_single_player
from .help_command import help_command
import random

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

# Handler for the game moves (if using text commands)
async def handle_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player_move = update.message.text.lower()
    # Make bot moves random for fair gameplay
    bot_move = random.choice(['rock', 'paper', 'scissors'])
    await update.message.reply_text(f"You chose {player_move}, I chose {bot_move}.")

# Callback query handler
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Always answer callback queries first
    
    if query.data == 'single_player':
        await start_single_player(update, context)
    elif query.data == 'multiplayer':
        await start_multiplayer(update, context)
    elif query.data == 'show_stats':
        await show_stats(update, context)
    elif query.data == 'help':
        await help_command(update, context)
