import os
import logging
import asyncio
import signal
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from handlers.start import start, start_callback, handle_bot_move
from handlers.mod import stats, leaderboard, achievements_callback, back_to_stats_callback, leaderboard_callback, admin_stats
from handlers.challenge import challenge, challenge_callback, move_callback, clear_challenges_command, handle_rematch
from handlers.data import manage_data_command, manage_data_callback
from database.connection import ensure_tables_exist, migrate_stats
from handlers.group_handler import add_group_handlers
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

async def shutdown(application):
    """Gracefully shut down the application."""
    logger.info("Shutting down bot...")
    await application.stop()
    await application.shutdown()
    logger.info("Bot shutdown complete.")

def handle_shutdown(loop, application):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    tasks = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    loop.run_until_complete(shutdown(application))
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
    logger.info("Event loop closed.")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error: {context.error}")

async def main():
    """Main function to run the bot."""
    logger.info("Initializing bot...")
    await ensure_tables_exist()
    await migrate_stats()
    
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
    
    add_group_handlers(app)
    app.add_error_handler(error_handler)

    # Set up signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_shutdown, loop, app)
    
    logger.info("Starting bot polling...")
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        # Keep the bot running until stopped
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        logger.info("Received shutdown signal, stopping bot...")
    finally:
        await shutdown(app)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
