from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_game_from_db, save_game_to_db, update_game_in_db, get_db_connection, get_cursor
import asyncio

async def start_multiplayer(callback_query):
    try:
        chat_id = callback_query.message.chat.id
        message_id = callback_query.message.message_id
        game_id = f"{chat_id}_{message_id}"
        caller_name = callback_query.from_user.first_name

        # Try to retrieve or create the game
        game = await get_game_from_db(game_id)
        if game is None:
            game = {'caller_name': caller_name, 'players': [caller_name], 'join_timer_active': True}
            await save_game_to_db(game_id, game)
        else:
            game['caller_name'] = caller_name
            game['players'] = [caller_name]
            game['join_timer_active'] = True
            await update_game_in_db(game_id, game)

        # Compact callback data to avoid length issues
        keyboard = [
            [InlineKeyboardButton("Challenge", callback_data=f'join_{game_id}')],
            [InlineKeyboardButton("Back to Menu", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await callback_query.edit_message_text(f"{caller_name} started a game! Waiting for challengers...", reply_markup=reply_markup)

        # Start the 30-second join timer
        await join_timer(callback_query, game_id)
    
    except Exception as e:
        await callback_query.message.reply_text("An error occurred while starting the multiplayer game.")
        print(f"Error in start_multiplayer: {e}")

async def join_timer(callback_query, game_id):
    try:
        await asyncio.sleep(30)  # Retain the 30-second timer
        game = await get_game_from_db(game_id)
        if game and len(game['players']) < 2:
            await callback_query.edit_message_text("Game Terminated due to insufficient players.")
            async with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM games WHERE game_id = ?', (game_id,))
                conn.commit()
        elif game:
            await start_multiplayer_game(callback_query, game_id)  # Define or import this function
    except Exception as e:
        await callback_query.message.reply_text("An error occurred during the game.")
        print(f"Error in join_timer: {e}")

async def start_multiplayer_game(callback_query, game_id):
    try:
        # Implement this function or import it if defined elsewhere
        pass
    except Exception as e:
        await callback_query.message.reply_text("An error occurred during the game.")
        print(f"Error in start_multiplayer_game: {e}")
