import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# Load the .env file
load_dotenv(dotenv_path='.env')

# Get the token from the .env file
Token = os.getenv("BOT_TOKEN")

# Check if the token is None
if not Token:
    raise ValueError("No token found. Please check your .env file.")

# Store player data
players = []
player_choices = {}

# Function to check if the bot is in a group chat
def in_group_chat(update: Update) -> bool:
    return update.effective_chat.type in ['group', 'supergroup']

# Start the game and allow players to join
def start(update: Update, context: CallbackContext) -> None:
    if not in_group_chat(update):
        update.message.reply_text("This game can only be played in a group chat.")
        return

    user = update.message.from_user

    if user.id not in players:
        players.append(user.id)
        player_choices[user.id] = None  # Initialize player's choice as None
        update.message.reply_text(f"{user.first_name} has joined the game!")
    else:
        update.message.reply_text("You have already joined the game!")

    if len(players) == 2:
        start_game(update, context)

# Start the Rock-Paper-Scissors game
def start_game(update: Update, context: CallbackContext) -> None:
    instructions = ("Welcome to Rock-Paper-Scissors!\n"
                    "Two players have joined the game.\n"
                    "Each player will receive a prompt to choose Rock, Paper, or Scissors.\n"
                    "The game will determine the winner once both players have made their choices.")

    update.message.reply_text(instructions)

    keyboard = [
        [
            InlineKeyboardButton("Rock", callback_data='rock'),
            InlineKeyboardButton("Paper", callback_data='paper'),
            InlineKeyboardButton("Scissors", callback_data='scissors'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for player_id in players:
        context.bot.send_message(chat_id=player_id, text="Choose Rock, Paper, or Scissors:", reply_markup=reply_markup)

# Handle the player's choice
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user = query.from_user

    if user.id in player_choices:
        player_choices[user.id] = query.data  # Save the player's choice
        query.answer()
        query.edit_message_text(text=f"You selected {query.data}")

        # Check if both players have made their choices
        if None not in player_choices.values():
            determine_winner(update, context)

# Determine the winner
def determine_winner(update: Update, context: CallbackContext) -> None:
    choice1 = player_choices[players[0]]
    choice2 = player_choices[players[1]]

    if choice1 == choice2:
        result = "It's a tie!"
    elif (choice1 == 'rock' and choice2 == 'scissors') or \
         (choice1 == 'scissors' and choice2 == 'paper') or \
         (choice1 == 'paper' and choice2 == 'rock'):
        result = f"Player 1 ({choice1}) beats Player 2 ({choice2})!"
    else:
        result = f"Player 2 ({choice2}) beats Player 1 ({choice1})!"

    # Announce the result in the group
    context.bot.send_message(chat_id=update.effective_chat.id, text=result)
    reset_game()

# Reset the game state
def reset_game() -> None:
    global players, player_choices
    players = []
    player_choices = {}

def main() -> None:
    # Initialize the Updater with the token from the .env file
    updater = Updater(Token)

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
