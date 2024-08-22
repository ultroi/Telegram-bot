import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Load the .env file
load_dotenv(dotenv_path='.env')

# Get the token from the .env file
Token = os.getenv("BOT_TOKEN")

# Check if the token is None
if not Token:
    raise ValueError("No token found. Please check your .env file.")

# Dictionary to store game data for each group chat
games = {}

# Function to check if the bot is in a group chat
def in_group_chat(update: Update) -> bool:
    return update.effective_chat.type in ['group', 'supergroup']

# Show instructions when /start is called
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    instructions = ("Welcome to the Rock-Paper-Scissors bot!\n\n"
                    "To start a new game, use /startgame in the group chat.\n"
                    "The first player to start the game will be Player 1.\n"
                    "The second player can join by pressing the 'Join' button.\n"
                    "Both players will choose Rock, Paper, or Scissors using inline buttons.\n"
                    "The result will be announced in the group chat.")
    await update.message.reply_text(instructions)

# Start a new game when /startgame is called
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if not in_group_chat(update):
        await update.message.reply_text("This game can only be played in a group chat.")
        return

    # Initialize the game state for the chat if it doesn't exist
    if chat_id not in games:
        games[chat_id] = {
            'players': [],
            'player_choices': {}
        }

    game = games[chat_id]

    if len(game['players']) == 0:
        user = update.message.from_user
        game['players'].append(user.id)
        game['player_choices'][user.id] = None  # Initialize player's choice as None
        await update.message.reply_text(f"{user.first_name} has started the game as Player 1!")

        # Provide a "Join" button for the second player
        join_button = [
            [InlineKeyboardButton("Join the Game", callback_data='join_game')]
        ]
        reply_markup = InlineKeyboardMarkup(join_button)
        await update.message.reply_text("Another player can join by clicking the button below:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("A game is already in progress. Please wait for it to finish before starting a new one.")

# Handle button clicks (join and choice selection)
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat_id
    game = games[chat_id]

    if query.data == 'join_game':
        if len(game['players']) == 1:
            game['players'].append(user.id)
            game['player_choices'][user.id] = None  # Initialize player's choice as None
            await query.edit_message_text(text=f"{user.first_name} has joined the game as Player 2!")
            await start_game_round(update, context)
        else:
            await query.answer("Two players have already joined.")
    elif query.data in ['rock', 'paper', 'scissors']:
        if user.id in game['player_choices']:
            game['player_choices'][user.id] = query.data  # Save the player's choice
            await query.answer()
            await query.edit_message_text(text=f"You selected {query.data}")

            # Check if both players have made their choices
            if None not in game['player_choices'].values():
                await determine_winner(update, context)

# Start the actual Rock-Paper-Scissors game round
async def start_game_round(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    game = games[chat_id]

    instructions = ("Both players have joined!\n"
                    "Each player will choose Rock, Paper, or Scissors using the buttons below.\n"
                    "The game will determine the winner once both players have made their choices.")

    await context.bot.send_message(chat_id=chat_id, text=instructions)

    keyboard = [
        [
            InlineKeyboardButton("Rock", callback_data='rock'),
            InlineKeyboardButton("Paper", callback_data='paper'),
            InlineKeyboardButton("Scissors", callback_data='scissors'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for player_id in game['players']:
        await context.bot.send_message(chat_id=player_id, text="Choose Rock, Paper, or Scissors:", reply_markup=reply_markup)

# Determine the winner
async def determine_winner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    game = games[chat_id]

    choice1 = game['player_choices'][game['players'][0]]
    choice2 = game['player_choices'][game['players'][1]]

    if choice1 == choice2:
        result = "It's a tie!"
    elif (choice1 == 'rock' and choice2 == 'scissors') or \
         (choice1 == 'scissors' and choice2 == 'paper') or \
         (choice1 == 'paper' and choice2 == 'rock'):
        result = f"Player 1 ({choice1}) beats Player 2 ({choice2})!"
    else:
        result = f"Player 2 ({choice2}) beats Player 1 ({choice1})!"

    # Announce the result in the group
    await context.bot.send_message(chat_id=chat_id, text=result)
    reset_game(chat_id)

# Reset the game state
def reset_game(chat_id: int) -> None:
    if chat_id in games:
        del games[chat_id]

def main() -> None:
    # Initialize the Application with the token from the .env file
    application = ApplicationBuilder().token(Token).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('startgame', start_game))
    application.add_handler(CallbackQueryHandler(button))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
