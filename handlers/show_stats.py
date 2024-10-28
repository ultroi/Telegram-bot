from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.connection import get_db_connection

# Show stats to the user
async def show_stats(client, message):
    user_id = message.from_user.id

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT wins, losses, ties FROM stats WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            wins, losses, ties = row
            message_text = (
                f"Here are your stats:\n"
                f"Wins: {wins}\n"
                f"Losses: {losses}\n"
                f"Ties: {ties}"
            )
        else:
            message_text = "No stats found for you. Start playing to record your stats!"

    keyboard = [
        [InlineKeyboardButton("Back to Menu", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(message_text, reply_markup=reply_markup)