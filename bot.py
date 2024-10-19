import os
import random
import logging
import asyncio
import sqlite3
from datetime import datetime, timedelta
import contextlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import contextlib
import telegram.error
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, Updater

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Developer ID
DEV_ID = 5956598856

# Establish a connection to the SQLite database
conn = sqlite3.connect('your_database.db')
cursor = conn.cursor()

# Ensure the 'games' table exists
cursor.execute('''
CREATE TABLE IF NOT EXISTS games (
    game_id TEXT PRIMARY KEY,
    multiplayer_moves TEXT,
    caller_name TEXT,
    players TEXT,
    join_timer_active BOOLEAN
)
''')
conn.commit()

# Ensure the 'stats' table exists
cursor.execute('''
CREATE TABLE IF NOT EXISTS stats (
    user_id INTEGER PRIMARY KEY,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    ties INTEGER DEFAULT 0
)
''')
conn.commit()

# Ensure the 'user_activity' table exists
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_activity (
    user_id INTEGER PRIMARY KEY,
    last_active TEXT
)
''')
conn.commit()

# Ensure the 'ban_list' table exists
cursor.execute('''
CREATE TABLE IF NOT EXISTS ban_list (
    user_id INTEGER PRIMARY KEY
)
''')
conn.commit()

# Example database interaction functions
def get_game_from_db(game_id):
    cursor.execute('SELECT multiplayer_moves, caller_name, players, join_timer_active FROM games WHERE game_id = ?', (game_id,))
    row = cursor.fetchone()
    if row:
        return {
            'multiplayer_moves': eval(row[0]) if row[0] else {},  # Convert string back to dictionary
            'caller_name': row[1],
            'players': eval(row[2]) if row[2] else [],  # Convert string back to list
            'join_timer_active': row[3]
        }
    return None

def save_game_to_db(game_id, game_data):
    cursor.execute('INSERT INTO games (game_id, multiplayer_moves, caller_name, players, join_timer_active) VALUES (?, ?, ?, ?, ?)', 
                   (game_id, str(game_data['multiplayer_moves']), game_data['caller_name'], str(game_data['players']), game_data['join_timer_active']))
    conn.commit()

def update_game_in_db(game_id, game_data):
    cursor.execute('UPDATE games SET multiplayer_moves = ?, caller_name = ?, players = ?, join_timer_active = ? WHERE game_id = ?', 
                   (str(game_data['multiplayer_moves']), game_data['caller_name'], str(game_data['players']), game_data['join_timer_active'], game_id))
    conn.commit()

def update_stats(user_id, result):
    cursor.execute('SELECT wins, losses, ties FROM stats WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        wins, losses, ties = row
        if result == 'win':
            wins += 1
        elif result == 'loss':
            losses += 1
        elif result == 'tie':
            ties += 1
        cursor.execute('UPDATE stats SET wins = ?, losses = ?, ties = ? WHERE user_id = ?', (wins, losses, ties, user_id))
    else:
        if result == 'win':
            cursor.execute('INSERT INTO stats (user_id, wins, losses, ties) VALUES (?, 1, 0, 0)', (user_id,))
        elif result == 'loss':
            cursor.execute('INSERT INTO stats (user_id, wins, losses, ties) VALUES (?, 0, 1, 0)', (user_id,))
        elif result == 'tie':
            cursor.execute('INSERT INTO stats (user_id, wins, losses, ties) VALUES (?, 0, 0, 1)', (user_id,))
    conn.commit()



# Predict the user's next move based on previous move history
def predict_user_move(user_id):
    cursor.execute('SELECT move FROM user_move_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 2', (user_id,))
    moves = cursor.fetchall()
    if len(moves) < 2:
        return random.choice(['rock', 'paper', 'scissors'])

    last_move = moves[0][0]
    move_counts = {'rock': 0, 'paper': 0, 'scissors': 0}

    for i in range(len(moves) - 1):
        if moves[i][0] == last_move:
            next_move = moves[i + 1][0]
            move_counts[next_move] += 1

    predicted_move = max(move_counts, key=move_counts.get)
    return predicted_move

# Determine counter-move to beat the user's move
def counter_move(move):
    if move == 'rock':
        return 'paper'
    elif move == 'paper':
        return 'scissors'
    else:
        return 'rock'

# Start command: Display main menu options
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Single Player 🎮", callback_data='single_player')],
        [InlineKeyboardButton("Multiplayer 👥", callback_data='multiplayer')],
        [InlineKeyboardButton("Stats 📊", callback_data='show_stats')],
        [InlineKeyboardButton("Help ❓", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to Rock Paper Scissors Bot! Choose an option:", reply_markup=reply_markup)

# Return to main menu
async def back_to_main_menu(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Single Player 🎮", callback_data='single_player')],
        [InlineKeyboardButton("Multiplayer 👥 (Group only)", callback_data='multiplayer')],
        [InlineKeyboardButton("Show Stats 📊", callback_data='show_stats')],
        [InlineKeyboardButton("Help ❓", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('Welcome back to Rock Paper Scissors! Choose a mode to start:', reply_markup=reply_markup)

# Check and delete inactive users
async def check_inactive_users():
    while True:
        current_time = datetime.now()
        cursor.execute('SELECT user_id, last_active FROM user_activity')
        users = cursor.fetchall()
        for user_id, last_active in users:
            if current_time - datetime.fromisoformat(last_active) > timedelta(days=7):
                cursor.execute('DELETE FROM user_activity WHERE user_id = ?', (user_id,))
                cursor.execute('DELETE FROM stats WHERE user_id = ?', (user_id,))
        conn.commit()
        await asyncio.sleep(86400)  # Check every 24 hours

# Handle mode selection (Single-player, Multiplayer, Stats, Help)
async def mode_selection(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    cursor.execute('INSERT OR REPLACE INTO user_activity (user_id, last_active) VALUES (?, ?)', (query.from_user.id, datetime.now().isoformat()))
    conn.commit()

    # Check if the user is banned
    cursor.execute('SELECT 1 FROM ban_list WHERE user_id = ?', (query.from_user.id,))
    if cursor.fetchone():
        await query.edit_message_text("You have been banned from using this bot.")
        return

    if query.data == 'single_player':
        await start_single_player(query)
    elif query.data == 'multiplayer':
        if update.effective_chat.type in ["group", "supergroup"]:
            await start_multiplayer(query, _)
        else:
            await query.edit_message_text("Multiplayer mode is only available in group chats.")
    elif query.data == 'show_stats':
        await show_stats(update, _)
    elif query.data == 'help':
        await help_command(update, _)
 

# Start single-player mode
async def start_single_player(query) -> None:
    keyboard = [
        [InlineKeyboardButton("Rock 🪨", callback_data='rock_bot')],
        [InlineKeyboardButton("Paper 📄", callback_data='paper_bot')],
        [InlineKeyboardButton("Scissors ✂️", callback_data='scissors_bot')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="You are playing against the bot! Choose your move:", reply_markup=reply_markup)

# Handle single-player moves
async def single_player_move(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    player_choice = query.data.split('_')[0]
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    result = determine_winner(player_choice, bot_choice)
    update_stats(query.from_user.id, result)

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
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')


# Start multiplayer mode (group-only)
async def start_multiplayer(query: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if query.message.chat.type not in ["group", "supergroup"]:
        await query.edit_message_text("Multiplayer mode is only available in group chats.")
        return

    chat_id = query.message.chat.id
    message_id = query.message.message_id
    game_id = f"{chat_id}_{message_id}"

    caller_name = query.from_user.first_name

    # Initialize the game data
    game = get_game_from_db(game_id)
    if game is None:
        game = {
        'caller_name': caller_name,
        'players': [caller_name],
        'join_timer_active': True
    }
        save_game_to_db(game_id, game)
    else:
        game['caller_name'] = caller_name
        game['players'] = [caller_name]
        game['join_timer_active'] = True
        update_game_in_db(game_id, game)

    # Create a Join Game button and start the timer
    keyboard = [
        [InlineKeyboardButton("Join Game", callback_data=f'join_multiplayer_{game_id}')],
        [InlineKeyboardButton("Back to Menu", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f"{caller_name} has started a multiplayer game! Waiting for another player to join... (60 seconds remaining)",
        reply_markup=reply_markup
    )

    # Start the join timer with countdown updates
    await join_timer(query, context, game_id)


# Helper function to check if the message content has changed
def message_needs_update(current_message, new_text, new_reply_markup):
    current_text = current_message.text
    current_reply_markup = current_message.reply_markup

    # Check if the text or reply markup has changed
    if current_text == new_text and current_reply_markup == new_reply_markup:
        return False
    return True


# Join timer for multiplayer game
async def join_timer(query: Update, context: ContextTypes.DEFAULT_TYPE, game_id: str):
    await asyncio.sleep(30)  # Wait for 30 seconds

    game = get_game_from_db(game_id)

    # Check if the game exists and has less than 2 players
    if game and len(game['players']) < 2:
        # New message and reply markup to update
        new_text = "Game has been terminated due to insufficient players. Please start again!"
        new_reply_markup = None  # No reply markup for terminated message

        # Check if the message needs updating before calling edit_message_text
        if message_needs_update(query.message, new_text, new_reply_markup):
            await query.message.edit_text(new_text)
        cursor.execute('DELETE FROM games WHERE game_id = ?', (game_id,))
        conn.commit()

    elif game:
        # New message and reply markup to start the game
        new_text = "The game is starting now!"
        new_reply_markup = None  # No reply markup for the starting message

        # Check if the message needs updating before calling edit_message_text
        if message_needs_update(query.message, new_text, new_reply_markup):
            await query.message.edit_text(new_text)

        await start_multiplayer_game(query, context, game_id)

    # Deactivate the join timer if game still exists
    if game:
        game['join_timer_active'] = False
        update_game_in_db(game_id, game)


# Join multiplayer game
async def join_multiplayer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    # Immediately answer the query to avoid expiration issues
    with contextlib.suppress(telegram.error.BadRequest):
        await query.answer()

    player_name = query.from_user.first_name
    game_id = query.data.split('_')[-1]

    game = get_game_from_db(game_id)

    if not game:
        # No need to update if the game doesn't exist anymore
        await query.edit_message_text("This game is no longer available.")
        return

    caller_name = game['caller_name']

    if player_name == caller_name:
        await query.answer("You cannot join your own game. Waiting for another player to join...", show_alert=True)
        return

    if len(game['players']) >= 2:
        await query.answer("The game is already full. Please wait for the next game.", show_alert=True)
        return

    game['players'].append(player_name)
    update_game_in_db(game_id, game)

    # Check if the game is now full (2 players)
    if len(game['players']) == 2:
        game['join_timer_active'] = False
        update_game_in_db(game_id, game)
        new_text = f"{player_name} has joined the game! The game will start shortly..."
        new_reply_markup = None

        # Only update the message if content has changed
        if message_needs_update(query.message, new_text, new_reply_markup):
            await query.edit_message_text(new_text)
        await start_multiplayer_game(query, context, game_id)
    else:
        new_text = f"{player_name} has joined the game! Waiting for another player to join..."
        new_reply_markup = query.message.reply_markup

        # Only update the message if content has changed
        if message_needs_update(query.message, new_text, new_reply_markup):
            await query.edit_message_text(new_text)


# Start multiplayer game
async def start_multiplayer_game(query: Update, context: ContextTypes.DEFAULT_TYPE, game_id: str):
    game = get_game_from_db(game_id)
    player1, player2 = game['players']

    # Player 1's move
    keyboard_p1 = [
        [InlineKeyboardButton("Rock 🪨", callback_data=f'rock_multiplayer_{player1}_{game_id}')],
        [InlineKeyboardButton("Paper 📄", callback_data=f'paper_multiplayer_{player1}_{game_id}')],
        [InlineKeyboardButton("Scissors ✂️", callback_data=f'scissors_multiplayer_{player1}_{game_id}')],
    ]
    reply_markup_p1 = InlineKeyboardMarkup(keyboard_p1)
    await query.message.reply_text(f"{player1}, choose your move:", reply_markup=reply_markup_p1)

    # Player 2's move
    keyboard_p2 = [
        [InlineKeyboardButton("Rock 🪨", callback_data=f'rock_multiplayer_{player2}_{game_id}')],
        [InlineKeyboardButton("Paper 📄", callback_data=f'paper_multiplayer_{player2}_{game_id}')],
        [InlineKeyboardButton("Scissors ✂️", callback_data=f'scissors_multiplayer_{player2}_{game_id}')],
    ]
    reply_markup_p2 = InlineKeyboardMarkup(keyboard_p2)
    await query.message.reply_text(f"{player2}, choose your move:", reply_markup=reply_markup_p2)


async def handle_game_end(query, game_id, player1, move1, result1, player2, move2, result2):
    game = get_game_from_db(game_id)
    if game is None:
        game = {'multiplayer_moves': []}
        save_game_to_db(game_id, game)

    update_stats(player2, result2)

    keyboard = [
        [InlineKeyboardButton("Play Again 🔄", callback_data=f'multiplayer_{game_id}')],
        [InlineKeyboardButton("Check Stats 📊", callback_data='show_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        f"{player1} chose {move1}. {player2} chose {move2}.\n"
        f"{player1}: {result1}\n"
        f"{player2}: {result2}"
    )
    
    with contextlib.suppress(Exception):  # Handle Telegram errors gracefully
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    game['multiplayer_moves'].clear()
    update_game_in_db(game_id, game)


async def handle_player_move(query, context, game_id, player_name, player_choice):
    game = get_game_from_db(game_id)
    if game is None:
        game = {'multiplayer_moves': {}}
        save_game_to_db(game_id, game)

    game['multiplayer_moves'][player_name] = player_choice
    update_game_in_db(game_id, game)

    if len(game['multiplayer_moves']) < 2:
        await query.edit_message_text(f"{player_name} has made their move. Waiting for the other player...")
        return

    # Both players have made their moves
    player1, player2 = list(game['multiplayer_moves'].keys())
    move1, move2 = game['multiplayer_moves'][player1], game['multiplayer_moves'][player2]

    result1 = determine_winner(move1, move2)
    result2 = determine_winner(move2, move1)

    await handle_game_end(query, game_id, player1, move1, result1, player2, move2, result2)


# Handle multiplayer move
async def multiplayer_move(update: Update) -> None:
    query = update.callback_query
    await query.answer()

    # Extracting player choice, name, and game ID from callback data
    try:
        player_choice = query.data.split('_')[1]
        player_name = query.data.split('_')[2]
        game_id = query.data.split('_')[-1]
    except IndexError:
        await query.edit_message_text("Invalid callback data. Please try again.")
        return

    # Fetch the game from the database
    game = get_game_from_db(game_id)
    if game is None:
        await query.edit_message_text("This game is no longer available.")
        return

    # Initialize multiplayer moves if not present
    if 'multiplayer_moves' not in game:
        game['multiplayer_moves'] = {}

    # Store the player's choice
    game['multiplayer_moves'][player_name] = player_choice
    update_game_in_db(game_id, game)

    # Check if both players have made their moves
    if len(game['multiplayer_moves']) < 2:
        await query.edit_message_text(f"{player_name} has made their move. Waiting for the other player...")
        return

    # Retrieve players and their moves
    player1, player2 = list(game['multiplayer_moves'].keys())
    move1, move2 = game['multiplayer_moves'][player1], game['multiplayer_moves'][player2]

    # Determine the winner
    result1 = determine_winner(move1, move2)
    result2 = determine_winner(move2, move1)

    # Handle the end of the game
    await handle_game_end(query, game_id, player1, move1, result1, player2, move2, result2)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # Log the error
        print(f"Update {update} caused error {context.error}")
        # Optionally, inform the user
        if update.effective_message:
            logger.error(f"Update {update} caused error {context.error}")
            if update.effective_message:
                await update.effective_message.reply_text("An error occurred. Please try again.")

# Show stats to the user
async def show_stats(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        query = update.callback_query
        await query.answer()  # Acknowledge the button press
        user_id = query.from_user.id
    else:
        user_id = update.message.from_user.id

    cursor.execute('SELECT wins, losses, ties FROM stats WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        wins, losses, ties = row
        message = (
            f"Here are your stats:\n"
            f"Wins: {wins}\n"
            f"Losses: {losses}\n"
            f"Ties: {ties}"
        )
    else:
        message = "No stats found for you. Start playing to record your stats!"

    keyboard = [
        [InlineKeyboardButton("Back to Menu", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await query.edit_message_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup)

# Determine the winner of the game
def determine_winner(player_choice, opponent_choice):
    outcomes = {
        'rock': {'rock': 'tie', 'paper': 'loss', 'scissors': 'win'},
        'paper': {'rock': 'win', 'paper': 'tie', 'scissors': 'loss'},
        'scissors': {'rock': 'loss', 'paper': 'win', 'scissors': 'tie'}
    }
    return outcomes[player_choice][opponent_choice]

# Show developer stats
async def show_dev_stats(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        query = update.callback_query
        await query.answer()  # Acknowledge the button press
    else:
        query = None

    # Example developer stats
    cursor.execute('SELECT COUNT(*) FROM games')
    total_games = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT chat_id) FROM user_activity WHERE chat_id < 0')
    total_groups = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM stats')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM user_activity WHERE last_active >= datetime("now", "-1 day")')
    active_users = cursor.fetchone()[0]

    message = (
        f"Developer Stats:\n"
        f"Total Games: {total_games}\n"
        f"Total Groups: {total_groups}\n"
        f"Total Users: {total_users}\n"
        f"Active Users (last 24h): {active_users}"
    )

    keyboard = [
        [InlineKeyboardButton("Back to Menu", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await query.edit_message_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup)

    # Help command: Display available commands
async def help_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        help_message = (
            "Help Menu:\n\n"
            "Here are the available commands:\n"
            "/start - Start the bot and choose a mode\n"
            "/ban <user_id> - Ban a user (Developer only)\n"
            "/unban <user_id> - Unban a user (Developer only)\n"
            "/dev_stats - Check developer stats (Developer only)\n"
            "/help - Show this help message\n"
        )

        keyboard = [
            [InlineKeyboardButton("Developer Commands", callback_data='dev_commands')],
            [InlineKeyboardButton("Back to Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(help_message, reply_markup=reply_markup)
        elif update.message:
            await update.message.reply_text(help_message, reply_markup=reply_markup)

    # Display developer commands
async def show_dev_commands(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        dev_commands_message = (
            "Developer Commands:\n\n"
            "/ban <user_id> - Ban a user from using the bot\n"
            "/unban <user_id> - Unban a user\n"
            "/dev_stats - Check user and game stats\n"
            "Use these commands responsibly!"
        )

        # Check if it's a callback query and respond accordingly
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(dev_commands_message)
        else:
            await update.message.reply_text(dev_commands_message)

        # Check if it's a callback query and respond accordingly
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(dev_commands_message)
        else:
            await update.message.reply_text(dev_commands_message)

# Main function to run the bot
def main():
    token = "7441832203:AAEV96F3k9qIH3rm-LyTUfG-0kTl_CeN4Lg"
    application = Application.builder().token(token).build()

        # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
#   application.add_handler(CommandHandler("ban", ban_user))
#   application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("show_stats", show_stats))
    application.add_handler(CommandHandler("dev_stats", show_dev_stats))

        # Callback query handler
    application.add_handler(CallbackQueryHandler(mode_selection, pattern='^(single_player|multiplayer|show_stats|help)$'))
    application.add_handler(CallbackQueryHandler(single_player_move, pattern='^(rock_bot|paper_bot|scissors_bot)$'))
    application.add_handler(CallbackQueryHandler(multiplayer_move, pattern='^(rock_multiplayer|paper_multiplayer|scissors_multiplayer)_.*$'))
    application.add_handler(CallbackQueryHandler(show_dev_commands, pattern='dev_commands'))
    application.add_handler(CallbackQueryHandler(back_to_main_menu, pattern='main_menu'))
    application.add_handler(CallbackQueryHandler(join_multiplayer, pattern='join_multiplayer_.*'))  # Update this line

        # Start checking for inactive users in the background
    loop = asyncio.get_event_loop()

        # Error handler
    application.add_error_handler(error_handler)
    loop.create_task(check_inactive_users())

        # Start the bot
    try:
        application.run_polling()
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                loop.run_until_complete(task)
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

if __name__ == "__main__":
    main()


