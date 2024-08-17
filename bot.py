from dotenv import load_dotenv
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext
import random

# Load the .env file
load_dotenv(dotenv_path='.env')

# Get the token from the .env file
Token = os.getenv("BOT_TOKEN")

# Check if the token is None
if not Token:
    raise ValueError("No token found. Please check your .env file.")

# Print the token for debugging (not recommended for production)
print(f"Token: {Token}")

# Define global variables
players = []
roles = ["Raja", "Chor", "Sipahi", "Mantri"]
scores = {}
rounds = 5
current_round = 0
mantri_id = None

# Database setup
conn = sqlite3.connect('game.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS players (user_id INTEGER PRIMARY KEY, score INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS games (game_id INTEGER PRIMARY KEY, current_round INTEGER)''')

# Commit changes and close the connection
conn.commit()

# Function to add or update player score
def update_player_score(user_id, score):
    try:
        c.execute('INSERT OR REPLACE INTO players (user_id, score) VALUES (?, ?)', (user_id, score))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error updating player score: {e}")

# Function to get player score
def get_player_score(user_id):
    try:
        c.execute('SELECT score FROM players WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        return result[0] if result else 0
    except sqlite3.Error as e:
        print(f"Error retrieving player score: {e}")
        return 0

# Reset the database
def reset_database():
    try:
        c.execute('DELETE FROM players')
        c.execute('DELETE FROM games')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error resetting database: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if update.message.chat.type == 'private':
        keyboard = [[InlineKeyboardButton("Start Game", callback_data='start_game')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Hello {user.first_name}, welcome to the game Raja Chor Sipahi Mantri!\n"
            "In this game, there are 4 roles: Raja, Chor, Sipahi, and Mantri. Each round, the roles are randomly assigned, and Mantri has to guess who the Chor is. Points are awarded based on the roles:\n"
            "Raja: 1000 points\nChor: 0 points\nSipahi: 100 points\nMantri: 500 points (or 0 if guess is wrong)\n"
            "The game has 5 rounds, and the player with the highest points at the end wins.\n"
            "Use /startgame in a group chat to begin the game.",
            reply_markup=reply_markup
        )
        context.user_data['interacted'] = True
    else:
        if context.user_data.get('interacted'):
            await update.message.reply_text("Use /startgame to begin the game.")
        else:
            await update.message.reply_text("Please send me a message in private chat first to interact with the bot.")

async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat.type != 'private':
        if context.user_data.get('interacted'):
            await update.message.reply_text("Game is starting! Use /join to participate. You have 1.5 minutes to join.")
            context.job_queue.run_once(remind_join, 60, chat_id=update.message.chat_id)
            context.job_queue.run_once(check_start_game, 90, chat_id=update.message.chat_id)
        else:
            await update.message.reply_text("Please interact with the bot in private chat first.")
    else:
        await update.message.reply_text("You can only use /startgame in a group chat.")

async def remind_join(context: CallbackContext) -> None:
    await context.bot.send_message(context.job.chat_id, text="30 seconds left to join the game! Use /join to participate.")

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            await start_game(chat_id, context)
    else:
        await update.message.reply_text("You are already in the game.")

async def start_game(chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    game = games.get(chat_id)
    if not game:
        return

    game['current_round'] += 1
    if game['current_round'] > rounds:
        await announce_results(chat_id, context)
        del games[chat_id]  # Remove the game from the dictionary
        return

    await context.bot.send_message(chat_id, text=f"Round {game['current_round']} is starting!")
    await assign_roles(chat_id, context)
    await context.bot.send_message(chat_id, text="Mantri, please guess who the Chor is by using /guess <player_name>")

async def check_start_game(context: CallbackContext) -> None:
    if len(players) < 4:
        await context.bot.send_message(context.job.chat_id, text="Not enough players joined. The game is ending.")
        reset_game()
    else:
        await start_game(context.job.chat_id, context)

# Reset the game state
def reset_game():
    global players, roles, current_round, mantri_id
    players = []
    roles = ["Raja", "Chor", "Sipahi", "Mantri"]
    current_round = 0
    mantri_id = None
    reset_database()  # Ensure this function properly clear s the database tables
    


async def assign_roles(chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            

async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global mantri_id
    user = update.message.from_user

    if user.id == mantri_id:
        try:
            if not context.args:
                raise IndexError("No player name provided.")
                
            guessed_player_name = context.args[0]
            guessed_player_id = next(player_id for player_id in players
                                      if (await context.bot.get_chat(player_id)).first_name == guessed_player_name)
            actual_chor_id = next(player_id for player_id, role in zip(players, roles) if role == "Chor")

            if guessed_player_id == actual_chor_id:
                await update.message.reply_text(f"Correct guess! {guessed_player_name} is the Chor.")
            else:
                actual_chor_name = (await context.bot.get_chat(actual_chor_id)).first_name
                await update.message.reply_text(f"Wrong guess! {guessed_player_name} is not the Chor. {actual_chor_name} is the actual Chor.")
                update_player_score(mantri_id, get_player_score(mantri_id) - 500)
        except (IndexError, StopIteration):
            await update.message.reply_text("Invalid guess. Please use /guess <player_name>")
        finally:
            await end_round(update.message.chat_id, context)
    else:
        await update.message.reply_text("You are not the Mantri. You cannot make a guess.")

async def end_round(chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    global current_round
    await context.bot.send_message(chat_id, text=f"Round {current_round} ended! Current scores:")
    
    for player_id in players:
        user = await context.bot.get_chat(player_id)
        await context.bot.send_message(chat_id, text=f"{user.first_name}: {get_player_score(player_id)} points")
    
    if current_round < rounds:
        await start_game(chat_id, context)
    else:
        await announce_results(context)
        reset_game()
        await context.bot.send_message(chat_id, text="The game has been reset. Use /startgame to start a new game.")

async def announce_results(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.chat_id if hasattr(context.job, 'chat_id') else context.job.chat_id
    await context.bot.send_message(chat_id, text="Game over! Final scores:")
    for player_id in players:
        user = await context.bot.get_chat(player_id)
        await context.bot
        

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if user.id in players:
        players.remove(user.id)
        update_player_score(user.id, 0)  # Remove player score from database
        await update.message.reply_text(f"{user.first_name} left the game. The game is ending.")
        await announce_results(context)
        reset_game()
        await update.message.reply_text("The game has been reset. Use /startgame to start a new game.")
        

# Dictionary to store game states
games = {}

# Initialize a new game
def start_new_game(chat_id):
    games[chat_id] = {
        'players': [],
        'roles': ["Raja", "Chor", "Sipahi", "Mantri"],
        'current_round': 0,
        'mantri_id': None
    }


def main() -> None:
    application = ApplicationBuilder().token(Token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("startgame", startgame))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("leave", leave))
    application.add_handler(CommandHandler("guess", guess))

    application.run_polling()

if __name__ == '__main__':
    main()
