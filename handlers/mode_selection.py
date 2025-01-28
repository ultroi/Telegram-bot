from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from .multiplayer import start_multiplayer, join_multiplayer, handle_multiplayer_move, handle_game_end, matchmaking_process
from .show_stats import show_stats
from .single_player import start_single_player
from .help_command import help_command

# Create the application
app = Application.builder().token("YOUR_BOT_TOKEN").build()

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

# Callback query handler
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'single_player':
        await start_single_player(update, context)
    elif query.data == 'multiplayer':
        await start_multiplayer(update, context)
    elif query.data == 'show_stats':
        await show_stats(update, context)
    elif query.data == 'help':
        await help_command(update, context)
