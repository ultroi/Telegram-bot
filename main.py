import asyncio
from pyrogram import Client, filters, idle
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from database.cleanup import cleanup_inactive_users
from database.connection import ensure_tables_exist
from handlers import start, handle_move, handle_callback_query, show_stats, help, start_single_player
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get credentials from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Initialize the Pyrogram client
app = Client("my_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Start the cleanup task
async def main():
    ensure_tables_exist()
    asyncio.create_task(cleanup_inactive_users())
    
    # Add other startup tasks here
    await app.start()
    
    # Register handlers
    app.add_handler(MessageHandler(start, filters.command("start")))
    app.add_handler(MessageHandler(handle_move, filters.text & ~filters.command("start")))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(show_stats, filters.command("show_stats")))
    app.add_handler(MessageHandler(help, filters.command("help")))
    app.add_handler(MessageHandler(start_single_player, filters.command("single_player")))
    
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())