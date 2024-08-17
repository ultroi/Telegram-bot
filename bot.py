from dotenv import load_dotenv
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
)

# Load the .env file
load_dotenv(dotenv_path='.env')

# Get the token from the .env file
Token = os.getenv("BOT_TOKEN")

# Check if the token is None
if not Token:
    raise ValueError("No token found. Please check your .env file.")

# Initialize logging
logging.basicConfig(level=logging.INFO)

# Database setup
def init_db():
    try:
        with sqlite3.connect('game.db') as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS players (user_id INTEGER PRIMARY KEY, score INTEGER, notified INTEGER DEFAULT 0)''')
            c.execute('''CREATE TABLE IF NOT EXISTS games (game_id INTEGER PRIMARY KEY, current_round INTEGER)''')
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

init_db()

# Dictionary to store game states
games = {}



def has_interacted(user_id):
    try:
        with sqlite3.connect('game.db') as conn:
            c = conn.cursor()
            c.execute("SELECT notified FROM players WHERE user_id=?", (user_id,))
            result = c.fetchone()
    except sqlite3.Error as e:
        logging.error(f"Database error in has_interacted: {e}")
        return False
    return result and result[0] == 1

def mark_as_interacted(user_id):
    try:
        with sqlite3.connect('game.db') as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO players (user_id, notified) VALUES (?, 1)", (user_id,))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database error in mark_as_interacted: {e}")

def update_player_score(player_id, new_score):
    try:
        with sqlite3.connect('game.db') as conn:
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO players (user_id, score) VALUES (?, ?)", (player_id, new_score))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database error in update_player_score: {e}")

def get_player_score(player_id):
    try:
        with sqlite3.connect('game.db') as conn:
            c = conn.cursor()
            c.execute("SELECT score FROM players WHERE user_id=?", (player_id,))
            result = c.fetchone()
    except sqlite3.Error as e:
        logging.error(f"Database error in get_player_score: {e}")
        return 0
    return result[0] if result else 0

def reset_database():
    try:
        with sqlite3.connect('game.db') as conn:
            c = conn.cursor()
            c.execute('DELETE FROM players')
            c.execute('DELETE FROM games')
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error resetting database: {e}")


def start_new_game(chat_id):
    games[chat_id] = {
        'players': [],
        'roles': ["Raja", "Chor", "Sipahi", "Mantri"],
        'current_round': 0,
        'mantri_id': None,
        'start_time': datetime.now() + timedelta(minutes=1.5)  # Game start time
    }

def reset_game(chat_id):
    if chat_id in games:
        del games[chat_id]
    reset_database()  # Ensure this function properly clears the database tables

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_first_name = update.message.from_user.first_name

    try:
        if has_interacted(user_id):
            await update.message.reply_text(f"Hello again, {user_first_name}! You've already interacted with me. How can I assist you today?")
        else:
            mark_as_interacted(user_id)
            welcome_message = (
                f"Welcome, {user_first_name}! 🤖\n\n"
                "I am your friendly neighborhood bot here to assist you with various tasks and games. "
                "You can start by using the following commands:\n\n"
                "/startgame - Start a new game in a group chat\n"
                "/join - Join an ongoing game\n"
                "/guess <player_name> - Mantri guesses the Chor\n"
                "/help - Show this help message\n\n"
                "Feel free to explore and let me know how I can help you today!"
            )
            await update.message.reply_text(welcome_message)
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        await update.message.reply_text("An error occurred while accessing the database. Please try again later.")

async def check_start_game(context: CallbackContext) -> None:
    chat_id = context.job.context['chat_id']
    game = games.get(chat_id)
    
    if game and len(game['players']) < 4:
        await context.bot.send_message(chat_id, text="Not enough players joined. The game is ending.")
        reset_game(chat_id)
        await context.bot.send_message(chat_id, text="Use /startgame to start a new game.")
    elif game and len(game['players']) == 4:
        await start_game(context.job.context['update'], context)
    else:
        await context.bot.send_message(chat_id, text="Game state error. Please use /startgame to start a new game.")

async def start_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    game = games.get(chat_id)

    if game:
        await context.bot.send_message(chat_id, text="A game is already running in this chat.")
        return

    start_new_game(chat_id)
    await context.bot.send_message(chat_id, text="Game is starting soon. Please use /join to join the game.")
    context.job_queue.run_once(check_start_game, 90, context={'chat_id': chat_id})

async def join(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    user = update.message.from_user
    
    if chat_id not in games:
        await update.message.reply_text("No game is currently running in this chat.")
        return

    if user.id not in games[chat_id]['players']:
        games[chat_id]['players'].append(user.id)
        update_player_score(user.id, 0)  # Initialize player score in database
        await update.message.reply_text(f"{user.first_name} joined the game!")

        if len(games[chat_id]['players']) == 4:
            await start_game(update, context)
    else:
        await update.message.reply_text("You are already in the game.")

async def assign_roles(chat_id, context: CallbackContext) -> None:
    game = games.get(chat_id)
    if not game or len(game['players']) != 4:
        raise ValueError("The game is not properly set up.")
    
    random.shuffle(game['players'])
    roles_assigned = dict(zip(game['players'], game['roles']))
    for player_id, role in roles_assigned.items():
        await context.bot.send_message(player_id, text=f"Your role: {role}")
        if role == "Raja":
            update_player_score(player_id, get_player_score(player_id) + 1000)
        elif role == "Sipahi":
            update_player_score(player_id, get_player_score(player_id) + 100)
        elif role == "Mantri":
            game['mantri_id'] = player_id
            update_player_score(player_id, get_player_score(player_id) + 500)

async def guess(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    chat_id = update.message.chat_id
    game = games.get(chat_id)

    if not game or user.id != game['mantri_id']:
        await update.message.reply_text("You are not the Mantri or the game is not active.")
        return

    if not context.args:
        await update.message.reply_text("Please use /guess <player_name>")
        return

    guessed_player_name = context.args[0]
    guessed_player_id = next(
        (player_id for player_id in game['players']
         if (await context.bot.get_chat(player_id)).first_name == guessed_player_name), 
        None
    )

    if guessed_player_id is None:
        await update.message.reply_text("Invalid guess. Please use /guess <player_name>")
        return

    actual_chor_id = next(
        (player_id for player_id, role in zip(game['players'], game['roles']) if role == "Chor"), 
        None
    )
    actual_chor_name = (await context.bot.get_chat(actual_chor_id)).first_name

    if guessed_player_id == actual_chor_id:
        await update.message.reply_text(f"Correct guess! {guessed_player_name} is the Chor.")
    else:
        await update.message.reply_text(f"Wrong guess! {guessed_player_name} is not the Chor. {actual_chor_name} is the actual Chor.")
        update_player_score(user.id, get_player_score(user.id) - 500)

    await end_round(chat_id, context)

async def end_round(chat_id, context: CallbackContext) -> None:
    game = games.get(chat_id)
    if not game:
        return

    # Update the game state or proceed to the next round
    game['current_round'] += 1
    if game['current_round'] < 5:
        await context.bot.send_message(chat_id, text=f"Round {game['current_round']} has ended. Starting next round...")
        # Assign new roles if needed
        await assign_roles(chat_id, context)
    else:
        await context.bot.send_message(chat_id, text="Game has ended.")
        reset_game(chat_id)

# Main function to run the bot
if __name__ == '__main__':
    application = ApplicationBuilder().token(Token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("startgame", start_game))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("guess", guess))

    application.run_polling()
    
