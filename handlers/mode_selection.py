from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
app = Client("my_bot")
from .multiplayer import start_multiplayer, join_multiplayer, handle_multiplayer_move, handle_game_end, matchmaking_process
from .single_player import start_single_player
from .show_stats import show_stats
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
@app.on_message(filters.command("start"))
async def start(client, message):
    keyboard = [
        [InlineKeyboardButton("Single Player", callback_data='single_player')],
        [InlineKeyboardButton("Multiplayer", callback_data='multiplayer')],
        [InlineKeyboardButton("Show Stats", callback_data='show_stats')],
        [InlineKeyboardButton("Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply("Welcome! Choose an option:", reply_markup=reply_markup)

# Handler for the game moves
@app.on_message(filters.text & ~filters.command)
async def handle_move(client, message):
    player_move = message.text.lower()
    bot_move = determine_bot_move(player_move)
    await message.reply(f"You chose {player_move}, I chose {bot_move}.")

# Callback query handler
@app.on_callback_query()
async def handle_callback_query(client, callback_query: CallbackQuery):
    if callback_query.data == 'single_player':
        await start_single_player(client, callback_query)
    elif callback_query.data == 'multiplayer':
        await start_multiplayer(client, callback_query)
    elif callback_query.data == 'show_stats':
        await show_stats(client, callback_query)
    elif callback_query.data == 'help':
        await help_command(client, callback_query)
