import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from database.connection import ensure_tables_exist
from handlers.start import start
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from handlers.stats import stats, leaderboard, achievements_callback, back_to_stats_callback, leaderboard_callback
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
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Register command handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CommandHandler("clearchallenges", clear_challenges_command))
app.add_handler(CommandHandler("challenge", challenge))
app.add_handler(CallbackQueryHandler(challenge_callback, pattern=r"^(accept|decline)_"))
app.add_handler(CallbackQueryHandler(move_callback, pattern=r"^move_(rock|paper|scissor)_"))
app.add_handler(CallbackQueryHandler(achievements_callback, pattern=r"^achievements_\d+$"))
app.add_handler(CallbackQueryHandler(back_to_stats_callback, pattern=r"^back_to_stats_\d+$"))
app.add_handler(CallbackQueryHandler(leaderboard_callback, pattern=r"^leaderboard_.*$"))


# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error: {context.error}")

application.add_error_handler(error_handler)

# Run the bot
if __name__ == "__main__":
    logger.info("Starting bot...")
    application.run_polling()
