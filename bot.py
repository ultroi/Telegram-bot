import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Global variables to manage the game
players = []
roles = ["Raja 👑", "Chor 🕵️‍♂️", "Sipahi 🛡", "Mantri 🤵"]
player_roles = {}
guessed_role = None

# /start command - Greets the user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Raja, Chor, Sipahi, Mantri game! Use /join to participate and /startgame to begin.")

# /join command - Adds a player to the game
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if len(players) < 4 and user.id not in players:
        players.append(user.id)
        await update.message.reply_text(f"{user.first_name} joined the game!")
    elif user.id in players:
        await update.message.reply_text("You are already in the game!")
    else:
        await update.message.reply_text("Game is full. Wait for the next round.")

# /startgame command - Starts the game by assigning roles
async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global player_roles
    if len(players) < 4:
        await update.message.reply_text("Not enough players! Need 4 players. Use /join to participate.")
    else:
        random.shuffle(players)
        player_roles = dict(zip(players, roles))
        
        # Notify each player of their role
        for player_id, role in player_roles.items():
            await context.bot.send_message(player_id, f"Your role is: {role}")
        
        await update.message.reply_text("Roles have been assigned! Mantri, use /guess to identify the 'Chor'.")

# /guess command - The Mantri guesses who the Chor is using buttons
async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global guessed_role
    if update.message.from_user.id not in players:
        await update.message.reply_text("You are not in the game! Use /join to participate.")
        return

    if player_roles.get(update.message.from_user.id) != "Mantri 🤵":
        await update.message.reply_text("Only the Mantri can guess!")
        return

    # Creating buttons for the Mantri to guess
    keyboard = [
        [InlineKeyboardButton(f"{await context.bot.get_chat(player_id).first_name}", callback_data=str(player_id))] for player_id in players if player_roles[player_id] != "Mantri 🤵"
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Who is the Chor? Make your guess:", reply_markup=reply_markup)

# Callback handler for the guess buttons
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global guessed_role
    query = update.callback_query
    await query.answer()
    
    guessed_player_id = int(query.data)
    guessed_role = player_roles[guessed_player_id]
    
    if guessed_role == "Chor 🕵️‍♂️":
        await query.edit_message_text(f"Correct! {await context.bot.get_chat(guessed_player_id).first_name} is the Chor! 🎉")
    else:
        await query.edit_message_text(f"Wrong guess! {await context.bot.get_chat(guessed_player_id).first_name} is not the Chor. 😔")
    
    reset_game()

# /leave command - Allows a player to leave the game
async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id in players:
        players.remove(user.id)
        await update.message.reply_text(f"{user.first_name} left the game.")
    else:
        await update.message.reply_text("You are not in the game!")

# /gstats command - Shows the current game status (for debugging)
async def gstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_message = "Current Players and Roles:\n"
    for player_id in players:
        user = await context.bot.get_chat(player_id)
        role = player_roles.get(player_id, "Not assigned")
        stats_message += f"{user.first_name} ({user.username}): {role}\n"
    await update.message.reply_text(stats_message)

# Reset the game after each round
def reset_game():
    global players, player_roles, guessed_role
    players = []
    player_roles = {}
    guessed_role = None

# Main function to start the bot
async def main():
    application = Application.builder().token("7528641996:AAFSMNIVRBLotZUcwepXAw_qQsiU5oGUG-0").build()

    # Define command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("startgame", startgame))
    application.add_handler(CommandHandler("guess", guess))
    application.add_handler(CommandHandler("leave", leave))
    application.add_handler(CommandHandler("gstats", gstats))
    application.add_handler(CallbackQueryHandler(button))

    # Start the bot
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
