import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from database.connection import ensure_tables_exist
from handlers.start import start
from handlers.play import play, button_callback
from handlers.challenge import challenge, challenge_callback, move_callback, clear_challenges_command
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get credentials from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables.")

# Build the application
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Register command handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("play", play))
application.add_handler(CallbackQueryHandler(button_callback))
application.add_handler(CommandHandler("challenge", challenge))
application.add_handler(CallbackQueryHandler(challenge_callback, pattern="^(accept|decline)_"))
application.add_handler(CommandHandler("clearchallenges", clear_challenges_command))
application.add_handler(CallbackQueryHandler(move_callback, pattern="^(🪨 Rock|📄 Paper|✂️ Scissor)"))

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error: {context.error}")

application.add_error_handler(error_handler)

# Run the bot
if __name__ == "__main__":
    logger.info("Starting bot...")
    application.run_polling()
