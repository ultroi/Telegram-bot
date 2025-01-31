from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# Start function 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = """
    🎮 <b>Welcome to Trihand!</b> 🎮
    🌟 Your ultimate Rock Paper Scissor companion! 🌟

    🪨✂️📜 <b>Bring your childhood game back to life!</b>
    Relive the fun and excitement of the classic Rock Paper Scissor game with a modern twist. Whether you're playing to pass the time or challenging friends, Trihand is here to make it fun and easy!

    💡 <i>Use /help to get more info and learn how to play.</i>

    Let's get started and see who wins! 🌟
    """
    await update.message.reply_text(intro, parse_mode=ParseMode.HTML)

