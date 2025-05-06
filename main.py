import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from handlers.start import start, start_callback, handle_bot_move
from handlers.mod import stats, leaderboard, achievements_callback, back_to_stats_callback, leaderboard_callback, admin_stats
from handlers.challenge import challenge, challenge_callback, move_callback, clear_challenges_command
from handlers.data import migrate_data_command, manage_data_callback
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
app.add_handler(CommandHandler("mdata", manage_data_command))
app.add_handler(CallbackQueryHandler(manage_data_callback, pattern="^(confirm_wipe_all|cancel_wipe_all|confirm_delete_user|cancel_delete_user|confirm_delete_group|cancel_delete_group)_"))

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error: {context.error}")

app.add_error_handler(error_handler)

# Run the bot
if __name__ == "__main__":
    logger.info("Starting bot...")
    app.run_polling()
