from dotenv import load_dotenv
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackContext, CallbackQueryHandler
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

# Database setup
conn = sqlite3.connect('game.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS players (user_id INTEGER PRIMARY KEY, score INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS games (game_id INTEGER PRIMARY KEY, current_round INTEGER)''')

# Commit changes and close the connection
conn.commit()

# Check if the user has interacted
def has_interacted(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("SELECT notified FROM players WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == 1:
        return True
    return False

# Mark user as interacted
def mark_as_interacted(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO players (user_id, notified) VALUES (?, 1)", (user_id,))
    conn.commit()
    conn.close()

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

async def some_function():
    # Code inside the function should be indented
    print("Hello, world!")

def get_player_data(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    
    try:
        c.execute("SELECT * FROM players WHERE user_id=?", (user_id,))
        player = c.fetchone()
        if player is None:
            return None
        return player
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
        return None
    finally:
        conn.close()

def update_player_notified(user_id, notified_status):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    
    try:
        c.execute("UPDATE players SET notified=? WHERE user_id=?", (notified_status, user_id))
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}")
    finally:
        conn.close()



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

# Reset the game state
def reset_game(chat_id):
    if chat_id in games:
        del games[chat_id]
    reset_database()  # Ensure this function properly clears the database tables

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    chat_id = update.message.chat_id
    
    # Check if the interaction flag is set
    c.execute('SELECT notified FROM players WHERE user_id = ?', (user.id,))
    result = c.fetchone()
    
    if result:
        notified = result[0]
    else:
        notified = 0
    
    if update.message.chat.type == 'private':
        if not notified:
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
            # Update the user as interacted
            c.execute('INSERT OR REPLACE INTO players (user_id, score, notified) VALUES (?, ?, ?)', (user.id, get_player_score(user.id), 1))
            conn.commit()
        else:
            await update.message.reply_text("You have already interacted with the bot.")
    else:
        if context.user_data.get('interacted'):
            await update.message.reply_text("Use /startgame to begin the game.")
        else:
            await update.message.reply_text("Please send me a message in private chat first to interact with the bot.")

async def startgame(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    user = update.message.from_user

    # Check if the user has interacted
    if has_interacted(user.id):
        if update.message.chat.type != 'private':
            await update.message.reply_text("Game is starting! Use /join to participate. You have 1.5 minutes to join.")
            context.job_queue.run_once(remind_join, 60, chat_id=chat_id)
            context.job_queue.run_once(check_start_game, 90, chat_id=chat_id)
            start_new_game(chat_id)  # Initialize the game state
        else:
            await update.message.reply_text("You can only use /startgame in a group chat.")
    else:
        await update.message.reply_text("Please interact with the bot in private chat first.")

async def join(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    user = update.message.from_user

    if chat_id not in games:
        await update.message.reply_text("No game is currently running in this chat.")
        return

    if user.id not in games[chat_id]['players']:
        games[chat_id]['players'].append(user.id)
        update_player_score(user.id, 0)  # Initialize player score in database
        mark_as_interacted(user.id)  # Mark user as interacted
        await update.message.reply_text(f"{user.first_name} joined the game!")

        if len(games[chat_id]['players']) == 4:
            await start_game(chat_id, context)
    else:
        await update.message.reply_text("You are already in the game.")

# Function to remind users to join the game
async def remind_join(context: CallbackContext) -> None:
    await context.bot.send_message(context.job.chat_id, text="30 seconds left to join the game! Use /join to participate.")

# Function to check if enough players have joined
async def check_start_game(context: CallbackContext) -> None:
    chat_id = context.job.chat_id
    game = games.get(chat_id)
    
    if game and len(game['players']) < 4:
        await context.bot.send_message(chat_id, text="Not enough players joined. The game is ending.")
        reset_game(chat_id)  # Reset the game state
        await context.bot.send_message(chat_id, text="Use /startgame to start a new game.")
    elif game and len(game['players']) == 4:
        await startgame(chat_id, context)
    else:
        await context.bot.send_message(chat_id, text="Game state error. Please use /startgame to start a new game.")

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
    # Your code here 
    pass  # Replace this with actual implementation 
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

async def end_round(chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Retrieve the game state for the given chat_id
    game = games.get(chat_id)
    if not game:
        return

    # Notify the chat that the round has ended
    await context.bot.send_message(chat_id, text=f"Round {game['current_round']} ended! Current scores:")

    # Prepare results to send
    results = []
    for player_id in game['players']:
        user = await context.bot.get_chat(player_id)
        score = get_player_score(player_id)
        results.append(f"{user.first_name}: {score} points")

    # Send the results to the chat
    await context.bot.send_message(chat_id, text="\n".join(results))

    # Check if the game should end or continue
    if game['current_round'] >= 5:
        await announce_results(chat_id, context)
        del games[chat_id]  # Remove game data for this chat
    else:
        game['current_round'] += 1
        await assign_roles(chat_id, context)  # Assign new roles for the next round

async def announce_results(chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    game = games.get(chat_id)
    if not game:
        return

    scores = [(player_id, get_player_score(player_id)) for player_id in game['players']]
    scores.sort(key=lambda x: x[1], reverse=True)

    results = ["Final scores:"]
    for player_id, score in scores:
        user = await context.bot.get_chat(player_id)
        results.append(f"{user.first_name}: {score} points")

    await context.bot.send_message(chat_id, text="\n".join(results))

    winner_id, winner_score = scores[0]
    winner = await context.bot.get_chat(winner_id)
    await context.bot.send_message(chat_id, text=f"The winner is {winner.first_name} with {winner_score} points!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "/start - Start interacting with the bot\n"
        "/startgame - Start a new game in a group chat\n"
        "/join - Join an ongoing game\n"
        "/guess <player_name> - Mantri guesses the Chor\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'start_game':
        await query.message.reply_text("Use /startgame in a group chat to begin the game.")

async def error_handler(update: Update, context: CallbackContext) -> None:
    print(f"Update {update} caused error {context.error}")



def main() -> None:
    # Initialize the application
    application = ApplicationBuilder().token(Token).build()

    # Add command handlers
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("startgame", startgame))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("guess", guess))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
