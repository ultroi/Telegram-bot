import asyncio
from pyrogram import Client, idle
from database.cleanup import cleanup_inactive_users
from database import ensure_tables_exist
from handlers.mode_selection import start, handle_move

# Initialize the Pyrogram client
app = Client("my_bot")

async def main():
    ensure_tables_exist()
    asyncio.create_task(cleanup_inactive_users())
    
    # Start the client
    await app.start()
    
    # Register handlers
    app.add_handler(start)
    app.add_handler(handle_move)
    
    # Keep the bot running
    await idle()
    
    # Stop the client when done
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())