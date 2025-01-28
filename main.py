import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from database.cleanup import cleanup_inactive_users
from database.connection import ensure_tables_exist
from handlers import start, handle_move, handle_callback_query, show_stats, help, start_single_player
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Main function to initialize the bot
async def main():
    # Ensure necessary database tables exist
    ensure_tables_exist()

    # Initialize the bot application
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("show_stats", show_stats))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("single_player", start_single_player))

    # Register message and callback query handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_move))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Start the bot
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
