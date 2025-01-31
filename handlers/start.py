from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes
from database.connection import get_db_connection  # Import database connection

# Start function 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command and add user to the database."""
    user = update.message.from_user
    profile_link = f"tg://user?id={user.id}"
    
    async with get_db_connection() as conn:
        await conn.execute('''
            INSERT INTO stats (user_id, first_name, last_name, profile_link)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
                first_name = excluded.first_name, 
                last_name = excluded.last_name, 
                profile_link = excluded.profile_link
        ''', (user.id, user.first_name, user.last_name or '', profile_link))
        await conn.commit()
    
    intro = """
    🎮 <b>Welcome to Trihand!</b> 🎮
    🌟 Your ultimate Rock Paper Scissor companion! 🌟

    🪨✂️📜 <b>Bring your childhood game back to life!</b>
    Relive the fun and excitement of the classic Rock Paper Scissor game with a modern twist. Whether you're playing to pass the time or challenging friends, Trihand is here to make it fun and easy!

    💡 <i>Use /help to get more info and learn how to play.</i>

    Let's get started and see who wins! 🌟
    """
    await update.message.reply_text(intro, parse_mode=ParseMode.HTML)
