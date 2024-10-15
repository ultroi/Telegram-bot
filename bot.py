import os
import random
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Developer ID
DEV_ID = 5956598856

# User move history for AI learning
user_move_history = {}
user_activity = {}
stats = {}
ban_list = {}
leaderboard_data = {}
unique_users = set()

def predict_user_move(user_id):
    if user_id not in user_move_history or len(user_move_history[user_id]) < 2:
        return random.choice(['rock', 'paper', 'scissors'])

    last_move = user_move_history[user_id][-1]
    move_counts = {'rock': 0, 'paper': 0, 'scissors': 0}

    for i in range(len(user_move_history[user_id]) - 1):
        if user_move_history[user_id][i] == last_move:
            next_move = user_move_history[user_id][i + 1]
            move_counts[next_move] += 1

    predicted_move = max(move_counts, key=move_counts.get)
    return predicted_move

def counter_move(move):
    if move == 'rock':
        return 'paper'
    elif move == 'paper':
        return 'scissors'
    else:
        return 'rock'

# Async start function
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Single Player", callback_data='single_player')],
        [InlineKeyboardButton("Multiplayer", callback_data='multiplayer')],
        [InlineKeyboardButton("Stats", callback_data='show_stats')],
        [InlineKeyboardButton("Help", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to Rock Paper Scissors Bot! Choose an option:", reply_markup=reply_markup)

async def help_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query  # Handle callback queries
    if query:
        await query.answer()  # Answer the callback query to remove the loading state
        keyboard = [
            [InlineKeyboardButton("Developer Commands", callback_data='dev_commands')],
            [InlineKeyboardButton("Back to Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        help_message = ("*Help Menu*:\n\n"
                        "Here are the available commands:\n"
                        "/start - Start the bot and choose a mode.\n"
                        "/ban <user_id> - Ban a user from using the bot (Developer only).\n"
                        "/unban <user_id> - Unban a user (Developer only).\n"
                        "/dev_stats - Check developer stats (Developer only).\n"
                        "/help - Show this help message.\n")

        await query.edit_message_text(help_message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        # If it's triggered by a message instead of a button click
        await update.message.reply_text(help_message, parse_mode='Markdown')

# Async function to show developer commands
async def show_dev_commands(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    dev_commands_message = ("*Developer Commands*:\n\n"
                            "/ban <user_id> - Ban a user from using the bot.\n"
                            "/unban <user_id> - Unban a user.\n"
                            "/dev_stats - Check stats related to users and games.\n"
                            "Use these commands responsibly!")

    await update.callback_query.edit_message_text(dev_commands_message, parse_mode='Markdown')

# Async function to handle back to main menu
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
    await query.edit_message_text('Welcome to Rock Paper Scissors! Choose a mode to start:', reply_markup=reply_markup)

# Function to check and delete inactive users
async def check_inactive_users():
    while True:
        current_time = datetime.now()
        for user_id in list(user_activity.keys()):
            if current_time - user_activity[user_id] > timedelta(days=7):
                del user_activity[user_id]
                if user_id in stats:
                    del stats[user_id]  # Optionally delete user stats as well
        await asyncio.sleep(86400)  # Check every day

# Async mode selection function
async def mode_selection(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_activity[query.from_user.id] = datetime.now()  # Update user activity
    unique_users.add(query.from_user.id)  # Add user to the set

    # Check if user is banned
    if query.from_user.id in ban_list:
        await query.edit_message_text("You have been banned from using this bot.")
        return

    if query.data == 'single_player':
        await start_single_player(query)
    elif query.data == 'multiplayer':
        if update.effective_chat.type in ["group", "supergroup"]:
            await start_multiplayer(query)
        else:
            await query.edit_message_text("Multiplayer mode is only available in group chats!")

# Async function for single-player mode
async def start_single_player(query) -> None:
    keyboard = [
        [InlineKeyboardButton("Rock 🪨", callback_data='rock_bot')],
        [InlineKeyboardButton("Paper 📄", callback_data='paper_bot')],
        [InlineKeyboardButton("Scissors ✂️", callback_data='scissors_bot')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="You are playing against the bot! Choose your move:", reply_markup=reply_markup)

# Async function to handle single-player moves
async def single_player_move(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_activity[query.from_user.id] = datetime.now()  # Update user activity

    player_choice = query.data.split('_')[0]  # Get player choice
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    result = determine_winner(player_choice, bot_choice)

    update_stats(query.from_user.first_name, result)  # Update user stats

    keyboard = [
        [InlineKeyboardButton("Play Again 🔄", callback_data='single_player')],
        [InlineKeyboardButton("Check Stats 📊", callback_data='show_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"You chose {player_choice}. Bot chose {bot_choice}. {result}", reply_markup=reply_markup)

# Async function for multiplayer mode
async def start_multiplayer(query, context) -> None:
    caller_name = query.from_user.first_name
    user_activity[query.from_user.id] = datetime.now()  # Update user activity
    context.user_data['caller_name'] = caller_name
    context.user_data['join_timer'] = asyncio.get_event_loop().create_task(join_timer(query))

    keyboard = [
        [InlineKeyboardButton("Rock 🪨", callback_data=f'rock_multiplayer_{caller_name}')],
        [InlineKeyboardButton("Paper 📄", callback_data=f'paper_multiplayer_{caller_name}')],
        [InlineKeyboardButton("Scissors ✂️", callback_data=f'scissors_multiplayer_{caller_name}')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"{caller_name} is playing multiplayer! Choose your move:", reply_markup=reply_markup)

# Async function for join timer
async def join_timer(query):
    await asyncio.sleep(60)  # 1-minute timer
    await query.edit_message_text("Game has been terminated due to inactivity. Please start again!")

# Async function to handle multiplayer move
async def multiplayer_move(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_activity[query.from_user.id] = datetime.now()  # Update user activity

    player_choice = query.data.split('_')[1]
    player_name = query.data.split('_')[2]

    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    result = determine_winner(player_choice, bot_choice)

    update_stats(player_name, result)  # Update user stats
    leaderboard_data[player_name] = stats[player_name]['wins']  # Update leaderboard data

    keyboard = [
        [InlineKeyboardButton("Play Again 🔄", callback_data='multiplayer')],
        [InlineKeyboardButton("Check Stats 📊", callback_data='show_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"{player_name} chose {player_choice}. Bot chose {bot_choice}. {result}", reply_markup=reply_markup)

# Utility function to determine the winner
def determine_winner(player_choice, bot_choice):
    if player_choice == bot_choice:
        return "It's a tie!"
    elif (player_choice == 'rock' and bot_choice == 'scissors') or \
         (player_choice == 'scissors' and bot_choice == 'paper') or \
         (player_choice == 'paper' and bot_choice == 'rock'):
        return "You win!"
    else:
        return "Bot wins!"

# Function to update stats
def update_stats(player_name, result):
    if player_name not in stats:
        stats[player_name] = {'wins': 0, 'losses': 0, 'ties': 0}

    if "win" in result:
        stats[player_name]['wins'] += 1
    elif "loss" in result:
        stats[player_name]['losses'] += 1
    else:
        stats[player_name]['ties'] += 1

# Command to show stats
async def show_stats(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.callback_query.from_user.first_name
    user_stats = stats.get(user_name, {'wins': 0, 'losses': 0, 'ties': 0})
    stats_message = (f"*Stats for {user_name}*:\n"
                     f"**Wins**: {user_stats['wins']}\n"
                     f"**Losses**: {user_stats['losses']}\n"
                     f"**Ties**: {user_stats['ties']}")

    keyboard = [
        [InlineKeyboardButton("Play Again", callback_data="play_again")],
        [InlineKeyboardButton("Exit", callback_data="exit")]
    ]

    await update.callback_query.edit_message_text(stats_message, parse_mode='Markdown')

# Command to show leaderboard
async def show_leaderboard(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    leaderboard_message = "🏆 **Leaderboard** 🏆\n"
    sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda item: item[1], reverse=True)

    for idx, (player_name, wins) in enumerate(sorted_leaderboard, start=1):
        leaderboard_message += f"{idx}. {player_name}: {wins} wins\n"

    await update.callback_query.edit_message_text(leaderboard_message)

# Developer command to check stats
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if update.effective_user.id != DEV_ID:
            await update.message.reply_text("You are not authorized to use this command.")
            return

        # Check if user_id was provided
        if len(context.args) != 1:
            await update.message.reply_text("Usage: /ban <user_id>")
            return

        user_id = int(context.args[0])
        if user_id in ban_list:
            await update.message.reply_text(f"User {user_id} is already banned.")
        else:
            ban_list[user_id] = True
            user_activity[user_id] = datetime.now()  # Update user activity for tracking
            await update.message.reply_text(f"User {user_id} has been banned.")
    except ValueError:
        await update.message.reply_text("Please provide a valid user ID.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if update.effective_user.id != DEV_ID:
            await update.message.reply_text("You are not authorized to use this command.")
            return

        # Check if user_id was provided
        if len(context.args) != 1:
            await update.message.reply_text("Usage: /unban <user_id>")
            return

        user_id = int(context.args[0])
        if user_id in ban_list:
            del ban_list[user_id]
            await update.message.reply_text(f"User {user_id} has been unbanned.")
        else:
            await update.message.reply_text(f"User {user_id} is not in the ban list.")
    except ValueError:
        await update.message.reply_text("Please provide a valid user ID.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")

# Command to display developer stats (active users, inactive users, etc.)
async def dev_stats(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        if update.effective_user.id != DEV_ID:
            await update.message.reply_text("You are not authorized to use this command.")
            return

        active_users = len(user_activity)
        inactive_users = len([user for user, last_active in user_activity.items() if datetime.now() - last_active > timedelta(days=7)])
        total_games = sum([user_stats['wins'] + user_stats['losses'] + user_stats['ties'] for user_stats in stats.values()])

        stats_message = (f"Developer Stats:\n"
                         f"Total Active Users: {active_users}\n"
                         f"Inactive Users: {inactive_users}\n"
                         f"Total Games Played: {total_games}\n"
                         f"Ban List: {', '.join([str(user) for user in ban_list.keys()])}")

        await update.message.reply_text(stats_message)
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")

def main() -> None:
    # Define your bot's token as an environment variable
    TOKEN = "7441832203:AAFI6Xxa_T5KC4kTLsdYlLHcwcx6jB3Yje4"

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(mode_selection, pattern='^(single_player|multiplayer|show_stats|help)$'))
    application.add_handler(CallbackQueryHandler(single_player_move, pattern='^(rock_bot|paper_bot|scissors_bot)$'))
    application.add_handler(CallbackQueryHandler(multiplayer_move, pattern='^(rock_multiplayer|paper_multiplayer|scissors_multiplayer)_.*$'))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("dev_stats", dev_stats))

    loop = asyncio.get_event_loop()
    loop.create_task(check_inactive_users())
    application.run_polling()

if __name__ == '__main__':
    main()
