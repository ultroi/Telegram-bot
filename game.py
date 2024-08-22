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
game_started = False

# Function to check if the bot is in a group chat
def in_group_chat(update: Update) -> bool:
    return update.effective_chat.type in ['group', 'supergroup']

# Show instructions when /start is called
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    instructions = ("🎉 Welcome to the Rock-Paper-Scissors bot! 🎉\n\n"
                    "Here's how to play:\n"
                    "1. To start a new game, use the /startgame command in the group chat.\n"
                    "2. The first player to start the game will be Player 1.\n"
                    "3. Others can join by clicking the 'Join the Game' button.\n"
                    "4. Once both players are in, you'll choose Rock, Paper, or Scissors using inline buttons.\n"
                    "5. The winner will be announced in the group chat.\n\n"
                    "Good luck and have fun! 🍀")
    await update.message.reply_text(instructions)


# Start a new game when /startgame is called
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id in games and len(games[chat_id]['players']) == 2:
        await update.message.reply_text("A game is already in progress.")
        return

    keyboard = [[InlineKeyboardButton("Join the Game", callback_data='join')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Click "Join the Game" to participate:', reply_markup=reply_markup)

    # Initialize game data for the chat if not already initialized
    if chat_id not in games:
        games[chat_id] = {
            'players': [],
            'player_choices': {}
        }
    

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    player_id = query.from_user.id
    chat_id = query.message.chat_id

    game = games.get(chat_id, None)
    if not game:
        await query.answer(text="No game is active in this chat.")
        return

    if player_id in game['players']:
        await query.answer(text="You have already joined.")
        return

    if len(game['players']) >= 2:
        await query.answer(text="The game is already full.")
        return

    # Add player to the game
    game['players'].append(player_id)
    game['player_choices'][player_id] = None  # Initialize player's choice as None
    await query.answer(text="You have joined the game!")

    if len(game['players']) == 2:
        await query.message.reply_text("Both players have joined. The game is starting!")
        await start_game_round(update, context)

# Handle button clicks (choice selection)
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    chat_id = update.effective_chat.id

    if chat_id not in games:
        await query.answer(text="No game is currently in progress.")
        return

    game = games[chat_id]

    if user.id not in game['players']:
        await query.answer(text="You are not part of this game.")
        return

    if query.data in ['rock', 'paper', 'scissors']:
        game['player_choices'][user.id] = query.data
        await query.answer()
        await query.edit_message_text(text=f"You selected {query.data }!")

        # Check if both players have made their choices
        if None not in game['player_choices'].values():
            await determine_winner(update, context)

# Start the actual Rock-Paper-Scissors game round
async def start_game_round(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    game = games[chat_id]

    instructions = ("📝 Both players have joined!\n\n"
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

    await context.bot.send_message(chat_id=chat_id, text="Both players, please make your choice:", reply_markup=reply_markup)

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
        result = f"Player 1 chose {choice1} and Player 2 chose {choice2}. Player 1 wins!"
    else:
        result = f"Player 1 chose {choice1} and Player 2 chose {choice2}. Player 2 wins!"

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
