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
c.execute('''CREATE TABLE IF NOT EXISTS players (user_id INTEGER PRIMARY KEY, score INTEGER, notified INTEGER DEFAULT 0)''')
c.execute('''CREATE TABLE IF NOT EXISTS games (game_id INTEGER PRIMARY KEY, current_round INTEGER)''')

# Commit changes
conn.commit()

# Remove erroneous cursor and connection usage
# cursor = connection.cursor
# cursor.execute('SELECT + FROMsome_table')
# Create tables if they don't exist

async def some_function():
    # Code inside the function should be indented
    print("Hello, world!")

# Check if the user has interacted
def has_interacted(user_id):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute("SELECT notified FROM players WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result and result[0] == 1

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
        conn = sqlite3.connect('game.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO players (user_id, score) VALUES (?, ?)', (user_id, score))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error updating player score: {e}")
    finally:
        conn.close()

# Function to get player score
def get_player_score(user_id):
    try:
        conn = sqlite3.connect('game.db')
        c = conn.cursor()
        c.execute('SELECT score FROM players WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        return result[0] if result else 0
    except sqlite3.Error as e:
        print(f"Error retrieving player score: {e}")
        return 0
    finally:
        conn.close()

# Reset the database
def reset_database():
    try:
        conn = sqlite3.connect('game.db')
        c = conn.cursor()
        c.execute('DELETE FROM players')
        c.execute('DELETE FROM games')
        conn.commit()
    except sqlite3.Error as e:
        print(f"Error resetting database: {e}")
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


# Ensure these are defined globally or within the appropriate context
conn = sqlite3.connect('database.db')  # Adjust to your database file path
cursor = conn.cursor()

def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_first_name = update.message.from_user.first_name

    try:
        # Check if the user has already interacted
        cursor.execute('SELECT interacted FROM user_interactions WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        if result and result[0] == 1:
            update.message.reply_text(f"Hello again, {user_first_name}! You've already interacted with me. How can I assist you today?")
        else:
            # If not, mark as interacted and send welcome message
            cursor.execute('REPLACE INTO user_interactions (user_id, interacted) VALUES (?, 1)', (user_id,))
            conn.commit()

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
            update.message.reply_text(welcome_message)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        update.message.reply_text("An error occurred while accessing the database. Please try again later.")
        

# Function to start the game
async def start_game(chat_id, context):
    game = games.get(chat_id)

    if not game:
        await context.bot.send_message(chat_id, text="No game is currently running in this chat.")
        return

    game['current_round'] += 1
    players = game['players']
    if len(players) < 4:
        await context.bot.send_message(chat_id, text="Not enough players to start the game.")
        return

    # Assign roles
    roles = ['Raja', 'Mantri', 'Sipahi', 'Chor']
    random.shuffle(roles)
    roles_assigned = dict(zip(players, roles))

    for player_id, role in roles_assigned.items():
        await context.bot.send_message(player_id, text=f"Your role is: {role}")

    # Notify the group about the roles
    await context.bot.send_message(chat_id, text="Roles have been assigned. Check your private messages.")

    # Example scoring mechanism
    for player_id, role in roles_assigned.items():
        if role == 'Raja':
            update_player_score(player_id, get_player_score(player_id) + 1000)
        elif role == 'Mantri':
            update_player_score(player_id, get_player_score(player_id) + 500)
        elif role == 'Sipahi':
            update_player_score(player_id, get_player_score(player_id) + 100)

    # Move to the next round or end the game
    if game['current_round'] < 5:
        context.job_queue.run_once(start_game, 300, context=chat_id)  # Schedule next round in 5 minutes
    else:
        await context.bot.send_message(chat_id, text="Game over!")
        reset_game(chat_id)

async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    user = update.message.from_user
    
    if chat_id not in games:
        await update.message.reply_text("No game is currently running in this chat.")
        return
    
    if user.id not in games[chat_id]['players']:
        games[chat_id]['players'].append(user.id)
        update_player_score(user.id, 0)  # Initialize player score in  database
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
        await start_game(chat_id, context)
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
    game = games.get(chat_id)
    if not game:
        return

    await context.bot.send_message(chat_id, text=f"Round {game['current_round']} ended! Current scores:")

    results = []
    for player_id in game['players']:
        user = await context.bot.get_chat(player_id)
        score = get_player_score(player_id)
        results.append(f"{user.first_name}: {score} points")

    await context.bot.send_message(chat_id, text="\n".join(results))

    if game['current_round'] >= 5:
        await announce_results(chat_id, context)
        del games[chat_id]
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
    application.add_handler(CommandHandler("startgame", start_game))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("guess", guess))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
