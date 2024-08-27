import telebot
from telebot import types
import time
import random
import uuid
import threading

bot = telebot.TeleBot('YOUR_API_KEY')

game_data = {}

# Game settings
best_of = 3
round_timeout = 60  # seconds
choice_timeout = 30  # seconds
min_players = 2
max_players = 4
auto_start_time = 30  # seconds to wait before auto-starting the game after the first player joins

def generate_game_id():
    return str(uuid.uuid4())

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Welcome to the Rock-Paper-Scissors bot! Type /play to start a game.")

@bot.message_handler(commands=['play'])
def play(message):
    if message.chat.type != 'group':
        bot.send_message(message.chat.id, "This bot only works in groups.")
        return

    markup = types.InlineKeyboardMarkup()
    btn_join = types.InlineKeyboardButton(text="Join Game", callback_data="join_game")
    markup.add(btn_join)
    bot.send_message(message.chat.id, f"A game has been started. Click the button to join. Maximum {max_players} players can join:", reply_markup=markup)

    game_data[message.chat.id] = {
        'players': 1,
        'bot_choice': None,
        'timeout': time.time() + round_timeout,
        'best_of': best_of,
        'scores': {},
        'choices': {message.from_user.id: None},
        'joined_players': [message.from_user.id],
        'game_id': generate_game_id(),
    }

    bot.send_message(message.chat.id, f"{message.from_user.first_name} has automatically joined the game.")

    start_auto_start_timer(message.chat.id)

def start_auto_start_timer(chat_id):
    if 'auto_start' in game_data[chat_id]:
        game_data[chat_id]['auto_start'].cancel()

    game_data[chat_id]['auto_start'] = threading.Timer(auto_start_time, auto_start_game, args=[chat_id])
    game_data[chat_id]['auto_start'].start()

def auto_start_game(chat_id):
    if chat_id in game_data:
        if game_data[chat_id]['players'] >= min_players:
            start_game(chat_id)
        else:
            markup = types.InlineKeyboardMarkup()
            btn_play_with_bot = types.InlineKeyboardButton(text="Play with Bot", callback_data="play_with_bot")
            markup.add(btn_play_with_bot)
            bot.send_message(chat_id, "No other players joined. Do you want to play with the bot?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('join_game'))
def handle_join(call):
    chat_id = call.message.chat.id
    if chat_id not in game_data or game_data[chat_id]['timeout'] <= time.time():
        return

    if game_data[chat_id]['players'] >= max_players:
        bot.send_message(chat_id, "The game is full. Maximum players reached.")
        return

    game_data[chat_id]['players'] += 1
    game_data[chat_id]['choices'][call.from_user.id] = None
    game_data[chat_id]['joined_players'].append(call.from_user.id)
    bot.send_message(chat_id, f"{call.from_user.first_name} has joined the game.")

    if game_data[chat_id]['players'] == min_players:
        start_game(chat_id)

@bot.callback_query_handler(func=lambda call: call.data == 'play_with_bot')
def play_with_bot(call):
    chat_id = call.message.chat.id
    if chat_id in game_data:
        game_data[chat_id]['players'] += 1  # Consider the bot as an additional player
        game_data[chat_id]['bot_choice'] = random.choice(['rock', 'paper', 'scissors'])
        start_game(chat_id)

def start_game(chat_id):
    if chat_id not in game_data:
        return

    game_data[chat_id]['auto_start'].cancel()

    markup = types.InlineKeyboardMarkup()
    btn_rock = types.InlineKeyboardButton(text="Rock", callback_data="choice_rock")
    btn_paper = types.InlineKeyboardButton(text="Paper", callback_data="choice_paper")
    btn_scissors = types.InlineKeyboardButton(text="Scissors", callback_data="choice_scissors")
    markup.add(btn_rock, btn_paper, btn_scissors)
    bot.send_message(chat_id, "The game is starting! Choose your weapon:", reply_markup=markup)

def evaluate_choices(chat_id):
    """Evaluates the choices of all players and determines the round winner."""

    choices = game_data[chat_id]['choices']
    bot_choice = game_data[chat_id].get('bot_choice', None)

    # ... (logic to compare choices and determine winner)

    # Example logic:
    winner_id = None
    winner_choice = None
    for player_id, choice in choices.items():
        if (choice == 'rock' and bot_choice == 'scissors') or \
           (choice == 'paper' and bot_choice == 'rock') or \
           (choice == 'scissors' and bot_choice == 'paper'):
            winner_id = player_id
            winner_choice = choice
            break
        elif choice == bot_choice:
            # It's a tie
            break

    # ... (update scores, send messages, etc.)


@bot.callback_query_handler(func=lambda call: call.data.startswith('choice_'))
def handle_choice(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    user_choice = call.data.split('_')[1]

    if user_id in game_data[chat_id]['choices'] and game_data[chat_id]['choices'][user_id] is not None:
        bot.send_message(chat_id, "You've already made your choice.")
        return

    game_data[chat_id]['choices'][user_id] = user_choice
    bot.send_message(chat_id, f"{call.from_user.first_name} chose {user_choice}.")

    if len([choice for choice in game_data[chat_id]['choices'].values() if choice is not None]) == game_data[chat_id]['players']:
        bot_choice = game_data[chat_id].get('bot_choice', random.choice(['rock', 'paper', 'scissors']))
        bot.send_message(chat_id, f"The bot chose {bot_choice}.")

        scores = {}
        for player_id, player_choice in game_data[chat_id]['choices'].items():
            if player_choice == bot_choice:
                scores[player_id] = 0
            elif (player_choice == 'rock' and bot_choice == 'scissors') or \
                 (player_choice == 'paper' and bot_choice == 'rock') or \
                 (player_choice == 'scissors' and bot_choice == 'paper'):
                scores[player_id] = 1
            else:
                scores[player_id] = 0

        winner_id = max(scores, key=scores.get)
        winner_score = scores[winner_id]

        if winner_score > 0:
            winner_name = bot.get_chat_member(chat_id, winner_id).user.first_name
            bot.send_message(chat_id, f"{winner_name} wins the round!")
        elif winner_score == 0:
            bot.send_message(chat_id, "It's a tie!")
        else:
            bot.send_message(chat_id, "The bot wins!")

        game_data[chat_id]['scores'][winner_id] = game_data[chat_id]['scores'].get(winner_id, 0) + 1

        if max(game_data[chat_id]['scores'].values()) == game_data[chat_id]['best_of']:
            winner_id = max(game_data[chat_id]['scores'], key=game_data[chat_id]['scores'].get)
            bot.send_message(chat_id, f"{bot.get_chat_member(chat_id, winner_id).user.first_name} wins the game!")
            del game_data[chat_id]
        else:
            bot.send_message(chat_id, f"The current score is: {game_data[chat_id]['scores']}")
            start_game(chat_id)

bot.polling()
