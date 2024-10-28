from datetime import datetime
from database.connection import get_db_connection
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.connection import get_db_connection, get_game_from_db, save_game_to_db, update_game_in_db, update_stats
from .single_player import start_single_player, single_player_move
from handlers.show_stats import show_stats
from handlers.help_command import help_command
from .multiplayer import start_multiplayer, join_multiplayer, handle_multiplayer_move, handle_game_end, matchmaking_process
from pyrogram import Client, filters

# Function to determine the bot's move
def determine_bot_move(player_move):
    if player_move == 'rock':
        return 'paper'
    elif player_move == 'paper':
        return 'scissors'
    else:
        return 'rock'

# Handler for the game moves
async def handle_move(client, message):
    player_move = message.text.lower()
    bot_move = determine_bot_move(player_move)
    await message.reply(f"You chose {player_move}, I chose {bot_move}.")

# Start command: Display main menu options
async def start(client, message):
    keyboard = [
        [InlineKeyboardButton("Single Player 🎮", callback_data='single_player')],
        [InlineKeyboardButton("Multiplayer 👥", callback_data='multiplayer')],
        [InlineKeyboardButton("Stats 📊", callback_data='show_stats')],
        [InlineKeyboardButton("Help ❓", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text("Welcome to Rock Paper Scissors Bot! Choose an option:", reply_markup=reply_markup)

# Return to main menu
async def back_to_main_menu(client, callback_query):
    await callback_query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Single Player 🎮", callback_data='single_player')],
        [InlineKeyboardButton("Multiplayer 👥 (Group only)", callback_data='multiplayer')],
        [InlineKeyboardButton("Show Stats 📊", callback_data='show_stats')],
        [InlineKeyboardButton("Help ❓", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await callback_query.edit_message_text('Welcome back to Rock Paper Scissors! Choose a mode to start:', reply_markup=reply_markup)

# Handle mode selection (Single-player, Multiplayer, Stats, Help)
async def mode_selection(client, callback_query):
    await callback_query.answer()
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO user_activity (user_id, last_active) VALUES (?, ?)', (callback_query.from_user.id, datetime.now().isoformat()))
        conn.commit()

        # Check if the user is banned
        cursor.execute('SELECT 1 FROM ban_list WHERE user_id = ?', (callback_query.from_user.id,))
        if cursor.fetchone():
            await callback_query.edit_message_text("You have been banned from using this bot.")
            return

    if callback_query.data == 'single_player':
        await start_single_player(callback_query)
    elif callback_query.data == 'multiplayer':
        if callback_query.message.chat.type in ["group", "supergroup"]:
            await start_multiplayer(callback_query)
        else:
            await callback_query.edit_message_text("Multiplayer mode is only available in group chats.")
    elif callback_query.data == 'show_stats':
        await show_stats(client, callback_query.message)
    elif callback_query.data == 'help':
        await help_command(client, callback_query.message)