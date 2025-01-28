from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from database.connection import get_db_connection

# Show stats to the user
async def show_stats(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    try:
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

        await update.message.reply_text(message_text, reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text("An error occurred while fetching your stats.")
        print(f"Error in show_stats: {e}")
