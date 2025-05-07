import os
import logging
import asyncio
import signal
from telegram import Update
from pathlib import Path
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ChatMemberHandler
from handlers.start import start, start_callback, handle_bot_move
from handlers.mod import stats, leaderboard, achievements_callback, back_to_stats_callback, leaderboard_callback, admin_stats
from handlers.challenge import challenge, challenge_callback, move_callback, clear_challenges_command, handle_rematch
from handlers.data import manage_data_command, manage_data_callback
from handlers.group_handler import chat_member_update
from database.connection import ensure_tables_exist
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Use absolute path for database file
DB_DIR = Path(__file__).parent.parent / "database"
DB_DIR.mkdir(exist_ok=True, mode=0o755)  # Ensure proper permissions
DB_PATH = DB_DIR / "trihand.db"

# Get credentials from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables.")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error: {context.error}")

async def main():
    """Main function to run the bot."""
    logger.info("Initializing bot...")
    
    try:
        # Initialize database with proper path handling
        await ensure_tables_exist()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("gstats", admin_stats))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("clearchallenges", clear_challenges_command))
    app.add_handler(CommandHandler("challenge", challenge))
    app.add_handler(CallbackQueryHandler(challenge_callback, pattern=r"^(accept|decline)_"))
    app.add_handler(CallbackQueryHandler(move_callback, pattern=r"^move_(rock|paper|scissor)_"))
    app.add_handler(CallbackQueryHandler(achievements_callback, pattern=r"^achievements_\d+$"))
    app.add_handler(CallbackQueryHandler(back_to_stats_callback, pattern=r"^back_to_stats_\d+$"))
    app.add_handler(CallbackQueryHandler(leaderboard_callback, pattern=r"^leaderboard_.*$"))
    app.add_handler(CallbackQueryHandler(start_callback, pattern="^(help|stats|quick_game|leaderboard|achievements|back_to_start)$"))
    app.add_handler(CallbackQueryHandler(handle_bot_move, pattern="^bot_move_"))
    app.add_handler(CallbackQueryHandler(handle_rematch, pattern="^rematch_"))
    app.add_handler(CommandHandler("mdata", manage_data_command))
    app.add_handler(CallbackQueryHandler(manage_data_callback, pattern="^(confirm_wipe_all|cancel_wipe_all|confirm_delete_user|cancel_delete_user|confirm_delete_group|cancel_delete_group)_"))
    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_error_handler(error_handler)

    # Enhanced shutdown handling
    async def enhanced_shutdown():
        """Enhanced shutdown procedure with database safety checks."""
        logger.info("Starting graceful shutdown...")
        try:
            if app.updater:
                await app.updater.stop()
            await app.stop()
            await app.shutdown()
            
            # Verify database file exists
            if not Path("data/trihand.db").exists():
                logger.warning("Database file not found after shutdown!")
            else:
                logger.info("Database file verified")
                
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            logger.info("Shutdown complete")

    # Signal handling with database protection
    def handle_signal(signame):
        logger.info(f"Received {signame}, initiating shutdown...")
        asyncio.create_task(enhanced_shutdown())

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: handle_signal(sig.name))

    # Startup checks
    logger.info("Running startup checks...")
    if not BOT_TOKEN:
        logger.error("No BOT_TOKEN found!")
        raise ValueError("BOT_TOKEN not set")
    
    if not Path("data/trihand.db").exists():
        logger.warning("No existing database found - creating new one")

    try:
        logger.info("Starting bot polling...")
        await app.initialize()
        await app.start()
        
        # Start updater with proper error handling
        if app.updater:
            await app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
        
        # Keep the bot running
        await asyncio.Event().wait()
        
    except asyncio.CancelledError:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        raise
    finally:
        await enhanced_shutdown()

if __name__ == "__main__":
    try:
        # Configure logging to file
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("bot.log"),
                logging.StreamHandler()
            ]
        )
        
        logger.info("Starting application...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Application failed: {e}")
        raise
