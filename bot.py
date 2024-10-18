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

# Store user activity, stats, ban list, and leaderboard
user_move_history = {}
user_activity = {}
stats = {}
ban_list = {}
leaderboard_data = {}
unique_users = set()

def escape_markdown_v2(text):
    escape_chars = ['.', '!', '~', '*', '_', '[', ']', '(', ')', '`', '#', '+', '-', '=', '|', '{', '}', '>', '<']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

# Predict the user's next move based on previous move history
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

# Help command: Display available commands
async def help_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    help_message = (
        "*Help Menu*:\n\n"
        "Here are the available commands:\n"
        "/start - Start the bot and choose a mode.\n"
        "/ban <user_id> - Ban a user (Developer only).\n"
        "/unban <user_id> - Unban a user (Developer only).\n"
        "/dev_stats - Check developer stats (Developer only).\n"
        "/help - Show this help message.\n"
    )

    if query:
        await query.answer()
        keyboard = [
            [InlineKeyboardButton("Developer Commands", callback_data='dev_commands')],
            [InlineKeyboardButton("Back to Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(help_message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.message.reply_text(help_message, parse_mode='Markdown')

# Display developer commands
async def show_dev_commands(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    dev_commands_message = (
        "*Developer Commands*:\n\n"
        "/ban <user_id> - Ban a user from using the bot.\n"
        "/unban <user_id> - Unban a user.\n"
        "/dev_stats - Check user and game stats.\n"
        "Use these commands responsibly!"
    )
    await update.callback_query.edit_message_text(dev_commands_message, parse_mode='Markdown')

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
        for user_id in list(user_activity.keys()):
            if current_time - user_activity[user_id] > timedelta(days=7):
                del user_activity[user_id]
                if user_id in stats:
                    del stats[user_id]  # Optionally delete user stats as well
        await asyncio.sleep(86400)  # Check every 24 hours

# Handle mode selection (Single-player, Multiplayer, Stats, Help)
async def mode_selection(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_activity[query.from_user.id] = datetime.now()  # Update user activity
    unique_users.add(query.from_user.id)  # Track unique users

    # Check if the user is banned
    if query.from_user.id in ban_list:
        await query.edit_message_text("You have been banned from using this bot.")
        return

    if query.data == 'single_player':
        await start_single_player(query)
    elif query.data == 'multiplayer':
        if update.effective_chat.type in ["group", "supergroup"]:
            await start_multiplayer(query, _)
        else:
            await query.edit_message_text("Multiplayer mode is only available in group chats.")

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
# Handle single-player moves
async def single_player_move(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    player_choice = query.data.split('_')[0]
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    result = determine_winner(player_choice, bot_choice)
    update_stats(query.from_user.first_name, result)  # Update stats

    keyboard = [
        [InlineKeyboardButton("Play Again 🔄", callback_data='single_player')],
        [InlineKeyboardButton("Check Stats 📊", callback_data='show_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Escaping special characters in MarkdownV2 format
    message = f"**You chose: {player_choice}\\.\nBot chose: {bot_choice}\\.\n{result}**"
    await query.edit_message_text(message, parse_mode="MarkdownV2", reply_markup=reply_markup)


# Start multiplayer mode (group-only)
async def start_multiplayer(query, context) -> None:
    caller_name = query.from_user.first_name
    context.user_data['caller_name'] = caller_name
    context.user_data['join_timer'] = asyncio.get_event_loop().create_task(join_timer(query))

    keyboard = [
        [InlineKeyboardButton("Rock 🪨", callback_data=f'rock_multiplayer_{caller_name}')],
        [InlineKeyboardButton("Paper 📄", callback_data=f'paper_multiplayer_{caller_name}')],
        [InlineKeyboardButton("Scissors ✂️", callback_data=f'scissors_multiplayer_{caller_name}')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text=f"{caller_name} is playing multiplayer! Choose your move:", reply_markup=reply_markup)

# Multiplayer join timer
async def join_timer(query):
    await asyncio.sleep(60)  # 1-minute timer
    await query.edit_message_text("Game has been terminated due to inactivity. Please start again!")

# Handle multiplayer move
async def multiplayer_move(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    player_choice = query.data.split('_')[1]
    player_name = query.data.split('_')[2]
    
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    result = determine_winner(player_choice, bot_choice)
    
    update_stats(player_name, result)
    leaderboard_data[player_name] = stats[player_name]['wins']  # Update leaderboard

    keyboard = [
        [InlineKeyboardButton("Play Again 🔄", callback_data='multiplayer')],
        [InlineKeyboardButton("Check Stats 📊", callback_data='show_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"{player_name} chose {player_choice}. Bot chose {bot_choice}. {result}", reply_markup=reply_markup)

# Determine the winner of the game
def determine_winner(player_choice, bot_choice):
    if player_choice == bot_choice:
        return "It's a tie!"
    elif (player_choice == 'rock' and bot_choice == 'scissors') or \
         (player_choice == 'paper' and bot_choice == 'rock') or \
         (player_choice == 'scissors' and bot_choice == 'paper'):
        return "You win!"
    else:
        return "Bot wins!"

# Update player stats
def update_stats(player_name, result):
    if player_name not in stats:
        stats[player_name] = {'wins': 0, 'losses': 0, 'ties': 0}
    
    if "win" in result.lower():
        stats[player_name]['wins'] += 1
    elif "tie" in result.lower():
        stats[player_name]['ties'] += 1
    else:
        stats[player_name]['losses'] += 1

# Show stats to the user
async def show_stats(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    player_name = query.from_user.first_name
    if player_name in stats:
        wins = stats[player_name]['wins']
        losses = stats[player_name]['losses']
        ties = stats[player_name]['ties']
        await query.edit_message_text(f"{player_name}, here are your stats:\nWins: {wins}\nLosses: {losses}\nTies: {ties}")
    else:
        await query.edit_message_text("No stats found for you. Start playing to record your stats!")

# Ban a user (Developer only)
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == DEV_ID:
        if len(context.args) > 0:
            user_id = int(context.args[0])
            ban_list[user_id] = True
            await update.message.reply_text(f"User {user_id} has been banned.")
        else:
            await update.message.reply_text("Please provide a user ID to ban.")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Unban a user (Developer only)
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == DEV_ID:
        if len(context.args) > 0:
            user_id = int(context.args[0])
            if user_id in ban_list:
                del ban_list[user_id]
                await update.message.reply_text(f"User {user_id} has been unbanned.")
            else:
                await update.message.reply_text(f"User {user_id} is not banned.")
        else:
            await update.message.reply_text("Please provide a user ID to unban.")
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Show developer stats (Developer only)
async def show_dev_stats(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id == DEV_ID:
        total_games = sum([stats[p]['wins'] + stats[p]['losses'] + stats[p]['ties'] for p in stats])
        active_users = len(user_activity)
        inactive_users = len(user_activity) - active_users
        
        await update.message.reply_text(
            f"Total games played: {total_games}\n"
            f"Active users: {active_users}\n"
            f"Inactive users: {inactive_users}"
        )
    else:
        await update.message.reply_text("You are not authorized to use this command.")

# Main function to run the bot
def main():
    token = "7441832203:AAEV96F3k9qIH3rm-LyTUfG-0kTl_CeN4Lg"
    application = Application.builder().token(token).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("dev_stats", show_dev_stats))

    # Callback query handler
    application.add_handler(CallbackQueryHandler(mode_selection, pattern='^(single_player|multiplayer|show_stats|help)$'))
    application.add_handler(CallbackQueryHandler(single_player_move, pattern='^(rock_bot|paper_bot|scissors_bot)$'))
    application.add_handler(CallbackQueryHandler(multiplayer_move, pattern='^(rock_multiplayer|paper_multiplayer|scissors_multiplayer)_.*$'))
    application.add_handler(CallbackQueryHandler(show_dev_commands, pattern='dev_commands'))
    application.add_handler(CallbackQueryHandler(back_to_main_menu, pattern='main_menu'))

    # Start checking for inactive users in the background
    loop = asyncio.get_event_loop()
    loop.create_task(check_inactive_users())

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()

