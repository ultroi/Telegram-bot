from database import get_game_from_db, save_game_to_db, update_game_in_db, get_db_connection
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio

async def start_multiplayer(bot, callback_query):
    try:
        chat_id = callback_query.message.chat.id
        message_id = callback_query.message.message_id
        game_id = f"{chat_id}_{message_id}"
        caller_name = callback_query.from_user.first_name

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
        await callback_query.edit_message_text(f"{caller_name} started a game! Waiting for challengers...", reply_markup=reply_markup)

        # Start the 30-second join timer
        await join_timer(bot, callback_query, game_id)
    
    except Exception as e:
        await callback_query.message.reply_text("An error occurred while starting the multiplayer game.")
        print(f"Error in start_multiplayer: {e}")

async def join_timer(bot, callback_query, game_id):
    try:
        await asyncio.sleep(30)  # Retain the 30-second timer
        game = get_game_from_db(game_id)
        if game and len(game['players']) < 2:
            await callback_query.edit_message_text("Game Terminated due to insufficient players.")
            async with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM games WHERE game_id = ?', (game_id,))
                conn.commit()
        elif game:
            await start_multiplayer_game(bot, callback_query, game_id)  # Define or import this function
    except Exception as e:
        await callback_query.message.reply_text("An error occurred during the game.")
        print(f"Error in join_timer: {e}")

async def start_multiplayer_game(bot, callback_query, game_id):
    try:
        # Implement this function or import it if defined elsewhere
        await callback_query.message.reply_text("Multiplayer game started!")
    except Exception as e:
        await callback_query.message.reply_text("An error occurred during the game.")
        print(f"Error in start_multiplayer_game: {e}")

async def join_multiplayer(bot, callback_query):
    try:
        game_id = callback_query.data.split('_')[1]
        user_name = callback_query.from_user.first_name

        game = get_game_from_db(game_id)
        if game and user_name not in game['players']:
            game['players'].append(user_name)
            update_game_in_db(game_id, game)
            await callback_query.answer(f"{user_name} joined the game!")
        else:
            await callback_query.answer("You are already in the game or the game does not exist.")
    except Exception as e:
        await callback_query.message.reply_text("An error occurred while joining the multiplayer game.")
        print(f"Error in join_multiplayer: {e}")

async def handle_multiplayer_move(bot, callback_query):
    try:
        game_id = callback_query.data.split('_')[1]
        user_name = callback_query.from_user.first_name
        move = callback_query.data.split('_')[2]  # Assuming the move is passed in the callback data

        game = get_game_from_db(game_id)
        if game and user_name in game['players']:
            # Implement the logic for handling the move
            # For example, updating the game state with the new move
            game['last_move'] = {'player': user_name, 'move': move}
            update_game_in_db(game_id, game)
            await callback_query.answer(f"{user_name} made a move: {move}")
            
            # Notify other players about the move
            other_players = [player for player in game['players'] if player != user_name]
            for player in other_players:
                # Assuming you have a way to send a message to other players
                await send_message_to_player(bot, player, f"{user_name} made a move: {move}")
        else:
            await callback_query.answer("You are not part of this game or the game does not exist.")
    except Exception as e:
        await callback_query.message.reply_text("An error occurred while handling the move.")
        print(f"Error in handle_multiplayer_move: {e}")

async def send_message_to_player(bot, player_name, message):
    try:
        async with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE user_name = ?', (player_name,))
            user_id = cursor.fetchone()
            if user_id:
                await bot.send_message(user_id[0], message)
            else:
                print(f"User {player_name} not found in the database.")
    except Exception as e:
        print(f"Error in send_message_to_player: {e}")

async def handle_game_end(bot, callback_query):
    try:
        game_id = callback_query.data.split('_')[1]
        async with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM games WHERE game_id = ?', (game_id,))
            conn.commit()
        await callback_query.message.reply_text("The game has ended.")
    except Exception as e:
        await callback_query.message.reply_text("An error occurred while ending the game.")
        print(f"Error in handle_game_end: {e}")

async def matchmaking_process(bot):
    try:
        async with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT game_id, players FROM games WHERE join_timer_active = 1')
            games = cursor.fetchall()

            for game_id, players in games:
                if len(players) >= 2:
                    await start_multiplayer_game(bot, game_id)
                    cursor.execute('UPDATE games SET join_timer_active = 0 WHERE game_id = ?', (game_id,))
                    conn.commit()
    except Exception as e:
        print(f"Error in matchmaking_process: {e}")
