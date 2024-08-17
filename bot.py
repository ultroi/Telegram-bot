from dotenv import load_dotenv
import random
from functools import partial
import os
import asyncio
import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackContext,
    JobQueue,
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

# Define constants manually if ParseMode is not available
MARKDOWN = 'Markdown'
HTML = 'HTML'

# Define the async send_message function 
async def send_message(update: Update, context: CallbackContext):
    result_message = "Your message here"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=result_message,
        parse_mode=ParseMode.HTML  # or ParseMode.MARKDOWN, depending on your needs
    )

# Define the callback function for the scheduled job
async def scheduled_task(context: CallbackContext):
    chat_id = context.job.context['chat_id']
    await context.bot.send_message(
        chat_id=chat_id,
        text="This is a scheduled message."
    )
    
def start_scheduled_job(job_queue: JobQueue, chat_id: int):
    """
    Schedules a task to be executed periodically or at a specific time.

    :param job_queue: The JobQueue instance from the application.
    :param chat_id: The chat ID where the scheduled task will operate.
    """
    job_queue.run_repeating(
        callback=scheduled_task,
        interval=3600,  # Interval in seconds (e.g., 3600 seconds = 1 hour)
        first=0,  # Start immediately
        context={'chat_id': chat_id}  # Pass context using a dictionary
    )

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
            c.execute("INSERT OR REPLACE INTO playe rs (user_id, notified) VALUES (?, 1)", (user_id,))
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database error in mark_as_interacte d: {e}")

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
                "/leave - you can left game\n"
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
        await context.bot.send_message(chat_id, text="Use /startgame@whothiefbot to start a new game.")
    elif game and len(game['players']) == 4:
        await start_game(context.job.context['update'], context)
    else:
        await context.bot.send_message(chat_id, text="Game state error. Please use /startgame@whothiefbot to start a new game.")




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


def start_new_game(chat_id):
    games[chat_id] = {
        'players': [],
        'roles': ['Raja', 'Chor', 'Sipahi', 'Mantri'],
        'current_round': 0,
        'mantri_id': None
    }

async def start_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id

    # Initialize a new game if none exists
    if chat_id not in games:
        start_new_game(chat_id)
    
    game = games[chat_id]

    if not game:
        await context.bot.send_message(chat_id, text="No game is currently running in this chat.")
        return

    players = game['players']
    
    if len(players) < 4:
        await context.bot.send_message(chat_id, text="Not enough players!! Need at least 4 players. Use /join@whothiefbot ")
        return

    # Assign roles
    roles = ['Raja', 'Mantri', 'Sipahi', 'Chor']
    random.shuffle(roles)
    roles_assigned = dict(zip(players, roles))

    # Notify players of their roles
    for player_id, role in roles_assigned.items():
        try:
            await context.bot.send_message(player_id, text=f"Your role is: {role}")
        except Exception as e:
            print(f"Failed to send role message to player {player_id}: {e}")

    # Notify the group with role assignment and game details
    player_names = {player_id: (await context.bot.get_chat(player_id)).first_name for player_id in players}
    player_points = {player_id: get_player_score(player_id) for player_id in players}
    
    game_start_message = (
        f"Roles have been assigned. Check your private messages.\n\n"
        f"Total Rounds: 5\n"
        f"Ongoing Round: 1\n\n"
        f"Players:\n"
        + "\n".join([f"{name}: {player_points[player_id]} points" for player_id, name in player_names.items()])
    )
    await context.bot.send_message(chat_id, text=game_start_message)

    # Example scoring mechanism
    for player_id, role in roles_assigned.items():
        if role == 'Raja':
            update_player_score(player_id, get_player_score(player_id) + 1000)
        elif role == 'Mantri':
            update_player_score(player_id, get_player_score(player_id) + 500)
            game['mantri_id'] = player_id  # Set Mantri
        elif role == 'Sipahi':
            update_player_score(player_id, get_player_score(player_id) + 100)

    # Handle rounds
    if game['current_round'] < 5:
        try:
            context.job_queue.run_once(
                callback=check_start_game,
                when=90,  # Time in seconds before the job is run
                context={'chat_id': chat_id}
            )
        except Exception as e:
            print(f"Failed to schedule job: {e}")
    else:
        await context.bot.send_message(chat_id, text="Game over!")
        reset_game(chat_id)

async def end_round(chat_id, context: CallbackContext) -> None:
    game = games.get(chat_id)
    if not game:
        return

    # Update the game state or proceed to the next round
    current_round = game['current_round']
    game['current_round'] += 1

    if game['current_round'] < 5:
        # Notify group about the end of the round and start of the new round
        player_names = {player_id: (await context.bot.get_chat(player_id)).first_name for player_id in game['players']}
        player_points = {player_id: get_player_score(player_id) for player_id in game['players']}

        round_end_message = (
            f"Round {current_round} has ended.\n"
            f"Round {game['current_round']} has started.\n\n"
            f"Total Rounds: 5\n"
            f"Ongoing Round: {game['current_round']}\n\n"
            f"Players:\n"
            + "\n".join([f"{name}: {player_points[player_id]} points" for player_id, name in player_names.items()])
        )
        await context.bot.send_message(chat_id, text=round_end_message)

        # Assign new roles if needed
        await assign_roles(chat_id, context)
    else:
        await context.bot.send_message(chat_id, text="Game has ended.")
        reset_game(chat_id)

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

    if not game:
        await update.message.reply_text("No game is currently running in this chat.")
        return

    if user.id != game['mantri_id']:
        await update.message.reply_text("You are not the Mantri or the game is not active.")
        return

    if not context.args:
        await update.message.reply_text("Please use /guess <username>")
        return

    guessed_username = context.args[0]

    # Get player details
    player_details = {player_id: await context.bot.get_chat(player_id) for player_id in game['players']}
    player_usernames = {player_id: details.username for player_id, details in player_details.items()}
    player_first_names = {player_id: details.first_name for player_id, details in player_details.items()}

    guessed_player_id = next(
        (player_id for player_id, username in player_usernames.items() if username == guessed_username), 
        None
    )

    if guessed_player_id is None:
        await update.message.reply_text("🤦🏼 Invalid guess. Please use /guess <username>")
        return

    actual_chor_id = next(
        (player_id for player_id, role in zip(game['players'], game['roles']) if role == "Chor"), 
        None
    )
    actual_chor_username = player_usernames[actual_chor_id]

    # Send result to group chat
    if guessed_player_id == actual_chor_id:
        result_message = f"🎉 *Correct guess!* [{guessed_username}](tg://user?id={guessed_player_id}) is the Chor. 🎉"
    else:
        result_message = (
            f"❌ *Wrong guess!* [{guessed_username}](tg://user?id={guessed_player_id}) is not the Chor.\n"
            f"👤 [{actual_chor_username}](tg://user?id={actual_chor_id}) is the actual Chor."
        )
        update_player_score(user.id, get_player_score(user.id) - 500)

    await context.bot.send_message(chat_id, text=result_message, parse_mode=ParseMode.MARKDOWN)

    # Reveal all players' roles
    roles_message = "🕵️ *Player Roles* 🕵️\n"
    for player_id, role in zip(game['players'], game['roles']):
        roles_message += f"👤 [{player_first_names[player_id]}](tg://user?id={player_id}) - {role}\n"

    await context.bot.send_message(chat_id, text=roles_message, parse_mode=ParseMode.MARKDOWN)

    await end_round(chat_id, context)

async def end_round(chat_id: int, context: CallbackContext) -> None:
    game = games.get(chat_id)
    if not game:
        return

    game['current_round'] += 1
    if game['current_round'] > game['total_rounds']:
        await announce_final_results(chat_id, context)
    else:
        await start_next_round(chat_id, context)

async def start_next_round(chat_id: int, context: CallbackContext):
    game = games[chat_id]
    current_round = game['current_round']
    total_rounds = game['total_rounds']
    mantri_id = game['mantri_id']
    mantri_details = await context.bot.get_chat(mantri_id)
    mantri_first_name = mantri_details.first_name

    # Message for the group chat with Mantri's role and players' roles
    roles_message = (
        f"🏁 *Round {current_round - 1} Ended* 🏁\n"
        f"🚀 *Round {current_round} Started* 🚀\n\n"
        f"{mantri_first_name}, you have 1 minute to guess the Chor! Use /guess <username>\n\n"
        f"*Players:* \n"
    )

    player_details = {player_id: await context.bot.get_chat(player_id) for player_id in game['players']}
    for player_id, role in zip(game['players'], game['roles']):
        player_first_name = player_details[player_id].first_name
        roles_message += f"👤 [{player_first_name}](tg://user?id={player_id}) - {role}\n"

    # Send roles message to the group chat
    await context.bot.send_message(chat_id, text=roles_message, parse_mode=ParseMode.MARKDOWN)

    # Notify all players privately about their roles
    for player_id, role in zip(game['players'], game['roles']):
        if player_id != mantri_id:
            role_message = f"Your role: {role}"
            await context.bot.send_message(player_id, text=role_message)

    # Set a 1-minute timer for the Mantri to make a guess
    await asyncio.sleep(60)  # 1 minute delay

    # Check if the Mantri has made a guess
    if game['current_round'] == current_round:
        # End the game if the Mantri did not guess
        await context.bot.send_message(chat_id, text=f"⏳ Time is up! {mantri_first_name} did not make a guess. The game is over.", parse_mode=ParseMode.MARKDOWN)
        await announce_final_results(chat_id, context)

async def announce_final_results(chat_id: int, context: CallbackContext):
    game = games[chat_id]
    result_message = "🏆 *Final Results* 🏆\n"
    player_details = {player_id: await context.bot.get_chat(player_id) for player_id in game['players']}
    for player_id in game['players']:
        player_first_name = player_details[player_id].first_name
        player_score = get_player_score(player_id)
        result_message += f"👤 [{player_first_name}](tg://user?id={player_id}) - {player_score} points\n"

    await context.bot.send_message(chat_id, text=result_message, parse_mode=ParseMode.MARKDOWN)
    del games[chat_id]

async def leave_game(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    chat_id = update.message.chat_id
    game = games.get(chat_id)

    if not game:
        await update.message.reply_text("No game is currently running in this chat.")
        return

    if user.id not in game['players']:
        await update.message.reply_text("You are not a participant in the current game.")
        return

    # Remove player from the game
    game['players'].remove(user.id)
    game['roles'].pop(game['players'].index(user.id))  # Remove the player's role

    # Notify all players about the departure
    departure_message = f"🚶 *[{user.first_name}](tg://user?id={user.id}) has left the game.* 🚶"
    await context.bot.send_message(chat_id, text=departure_message, parse_mode=ParseMode.MARKDOWN)

    # Check if only one player is left
    if len(game['players']) == 1:
        remaining_player_id = game['players'][0]
        remaining_player_details = await context.bot.get_chat(remaining_player_id)
        remaining_player_first_name = remaining_player_details.first_name

        # Notify remaining player and end the game
        result_message = (
            f"🚫 *The game has been ended because you are the only player left.* 🚫\n"
            f"👤 [{remaining_player_first_name}](tg://user?id={remaining_player_id}) is the last player."
        )
        await context.bot.send_message(chat_id, text=result_message, parse_mode=ParseMode.MARKDOWN)

        # Clear game data
        del games[chat_id]
    else:
        # Optionally, update remaining players about the new game status
        status_message = "📋 *Updated Game Status* 📋\n"
        for player_id in game['players']:
            player_details = await context.bot.get_chat(player_id)
            player_first_name = player_details.first_name
            status_message += f"👤 [{player_first_name}](tg://user?id={player_id})\n"
        await context.bot.send_message(chat_id, text=status_message, parse_mode=ParseMode.MARKDOWN)
        

async def main():
    # Initialize the bot application
    application = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()
    job_queue = application.job_queue

    # Schedule the task
    start_scheduled_job(job_queue, chat_id=123456789)

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("startgame", start_game))
    application.add_handler(CommandHandler("join", join))
    application.add_handker(CommandHandler('some_command',handle_command))
    application.add_handler(CommandHandler("leave", leave_game))
    application.add_handler(CommandHandler("guess", guess))

    # Start polling
    await application.run_polling()

async def shutdown(application):
    # Stop the application gracefully
    await application.stop()
    await application.wait_closed()

if __name__ == '__main__':
    # Run the bot application with proper shutdown handling
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        # Handle graceful shutdown on exit
        print("Stopping bot...")
        asyncio.run(shutdown(application))


