from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CallbackQueryHandler, CommandHandler, MessageHandler, Filters
from database import get_game_from_db, save_game_to_db, update_game_in_db, get_db_connection
import asyncio

# Function to determine bot's move (similar to your previous logic)
def determine_bot_move(player_move):
    if player_move == 'rock':
        return 'paper'
    elif player_move == 'paper':
        return 'scissors'
    else:
        return 'rock'

# Start Multiplayer Game
async def start_multiplayer(update: Update, context):
    try:
        chat_id = update.message.chat.id
        message_id = update.message.message_id
        game_id = f"{chat_id}_{message_id}"
        caller_name = update.message.from_user.first_name

        # Try to retrieve or create the game
        game = get_game_from_db(game_id)
        if game is None:
            game = {'caller_name': caller_name, 'players': [caller_name], 'join_timer_active': True}
            save_game_to_db(game_id, game)
        else:
            game['caller_name'] = caller_name
            game['players'] = [caller_name]
            game['join_timer_active'] = True
            update_game_in_db(game_id, game)

        # Compact callback data to avoid length issues
        keyboard = [
            [InlineKeyboardButton("Challenge", callback_data=f'join_{game_id}')],
            [InlineKeyboardButton("Back to Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.edit_text(f"{caller_name} started a game! Waiting for challengers...", reply_markup=reply_markup)

        # Start the 30-second join timer
        await join_timer(update, context, game_id)

    except Exception as e:
        await update.message.reply_text("An error occurred while starting the multiplayer game.")
        print(f"Error in start_multiplayer: {e}")

# Join timer after 30 seconds
async def join_timer(update: Update, context, game_id):
    try:
        await asyncio.sleep(30)  # Retain the 30-second timer
        game = get_game_from_db(game_id)
        if game and len(game['players']) < 2:
            await update.message.edit_text("Game Terminated due to insufficient players.")
            async with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM games WHERE game_id = ?', (game_id,))
                conn.commit()
        elif game:
            await start_multiplayer_game(update, context, game_id)  # Define or import this function
    except Exception as e:
        await update.message.reply_text("An error occurred during the game.")
        print(f"Error in join_timer: {e}")

# Start multiplayer game (can be expanded)
async def start_multiplayer_game(update: Update, context, game_id):
    try:
        await update.message.reply_text("Multiplayer game started!")
    except Exception as e:
        await update.message.reply_text("An error occurred during the game.")
        print(f"Error in start_multiplayer_game: {e}")

# Join the multiplayer game
async def join_multiplayer(update: Update, context):
    try:
        game_id = update.callback_query.data.split('_')[1]
        user_name = update.callback_query.from_user.first_name

        game = get_game_from_db(game_id)
        if game and user_name not in game['players']:
            game['players'].append(user_name)
            update_game_in_db(game_id, game)
            await update.callback_query.answer(f"{user_name} joined the game!")
        else:
            await update.callback_query.answer("You are already in the game or the game does not exist.")
    except Exception as e:
        await update.message.reply_text("An error occurred while joining the multiplayer game.")
        print(f"Error in join_multiplayer: {e}")

# Handle multiplayer move
async def handle_multiplayer_move(update: Update, context):
    try:
        game_id = update.callback_query.data.split('_')[1]
        user_name = update.callback_query.from_user.first_name
        move = update.callback_query.data.split('_')[2]  # Assuming the move is passed in the callback data

        game = get_game_from_db(game_id)
        if game and user_name in game['players']:
            # Implement the logic for handling the move
            game['last_move'] = {'player': user_name, 'move': move}
            update_game_in_db(game_id, game)
            await update.callback_query.answer(f"{user_name} made a move: {move}")

            # Notify other players about the move
            other_players = [player for player in game['players'] if player != user_name]
            for player in other_players:
                await send_message_to_player(update, player, f"{user_name} made a move: {move}")
        else:
            await update.callback_query.answer("You are not part of this game or the game does not exist.")
    except Exception as e:
        await update.message.reply_text("An error occurred while handling the move.")
        print(f"Error in handle_multiplayer_move: {e}")

# Send message to a specific player
async def send_message_to_player(update: Update, player_name, message):
    try:
        async with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE user_name = ?', (player_name,))
            user_id = cursor.fetchone()
            if user_id:
                await update.message.bot.send_message(user_id[0], message)
            else:
                print(f"User {player_name} not found in the database.")
    except Exception as e:
        print(f"Error in send_message_to_player: {e}")

# Handle game end
async def handle_game_end(update: Update, context):
    try:
        game_id = update.callback_query.data.split('_')[1]
        async with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM games WHERE game_id = ?', (game_id,))
            conn.commit()
        await update.callback_query.message.reply_text("The game has ended.")
    except Exception as e:
        await update.callback_query.message.reply_text("An error occurred while ending the game.")
        print(f"Error in handle_game_end: {e}")

# Matchmaking process
async def matchmaking_process(update: Update, context):
    try:
        async with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT game_id, players FROM games WHERE join_timer_active = 1')
            games = cursor.fetchall()

            for game_id, players in games:
                if len(players) >= 2:
                    await start_multiplayer_game(update, context, game_id)
                    cursor.execute('UPDATE games SET join_timer_active = 0 WHERE game_id = ?', (game_id,))
                    conn.commit()
    except Exception as e:
        print(f"Error in matchmaking_process: {e}")
