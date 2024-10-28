from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.connection import update_stats
import random

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
async def single_player_move(client, callback_query):
    await callback_query.answer()
    
    player_choice = callback_query.data.split('_')[0]
    bot_choice = random.choice(['rock', 'paper', 'scissors'])
    result = determine_winner(player_choice, bot_choice)
    update_stats(callback_query.from_user.id, result)

    keyboard = [
        [InlineKeyboardButton("Play Again 🔄", callback_data='single_player')],
        [InlineKeyboardButton("Check Stats 📊", callback_data='show_stats')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = (
        f"**You chose:** {player_choice} 🪨📄✂️\n"
        f"**Bot chose:** {bot_choice} 🤖\n"
        f"**{result}** 🎉"
    )
    await callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

# Determine the winner of the game
def determine_winner(player_choice, opponent_choice):
    outcomes = {
        'rock': {'rock': 'tie', 'paper': 'loss', 'scissors': 'win'},
        'paper': {'rock': 'win', 'paper': 'tie', 'scissors': 'loss'},
        'scissors': {'rock': 'loss', 'paper': 'win', 'scissors': 'tie'}
    }
    return outcomes[player_choice][opponent_choice]