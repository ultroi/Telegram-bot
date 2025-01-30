import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from database.cleanup import cleanup_inactive_users
from database.connection import ensure_tables_exist
from handlers import start, handle_move, handle_callback_query, show_stats, help, start_single_player
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

# Initialize database
ensure_tables_exist()
cleanup_inactive_users()  # Optional: Clean up inactive users on startup

# Build the application
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Register command handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("show_stats", show_stats))
application.add_handler(CommandHandler("help", help))
application.add_handler(CommandHandler("single_player", start_single_player))

# Register message and callback query handlers
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_move))
application.add_handler(CallbackQueryHandler(handle_callback_query))

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error: {context.error}")

application.add_error_handler(error_handler)

# Run the bot
if __name__ == "__main__":
    logger.info("Starting bot...")
    application.run_polling()
