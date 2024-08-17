from dotenv import load_dotenv
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackContext
import random

load_dotenv()
Token = os.getenv("BOT_TOKEN")

# Define global variables
players = []
roles = ["Raja", "Chor", "Sipahi", "Mantri"]
scores = {}
rounds = 5
current_round = 0
mantri_id = None

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if update.message.chat.type == 'private':
        await update.message.reply_text(f"Hello {user.first_name}, welcome to the game Raja Chor Sipahi Mantri!\n"
                                        "In this game, there are 4 roles: Raja, Chor, Sipahi, and Mantri. Each round, the roles are randomly assigned, and Mantri has to guess who the Chor is. Points are awarded based on the roles:\n"
                                        "Raja: 1000 points\nChor: 0 points\nSipahi: 100 points\nMantri: 500 points (or 0 if guess is wrong)\n"
                                        "The game has 5 rounds, and the player with the highest points at the end wins.\n"
                                        "Use /startgame in a group chat to begin the game.")
        context.user_data['interacted'] = True
    else:
        if context.user_data.get('interacted'):
            await update.message.reply_text("Use /startgame to begin the game.")
        else:
            await update.message.reply_text("Please send me a message in private chat first to interact with the bot.")

async def startgame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat.type != 'private':
        if context.user_data.get('interacted'):
            await update.message.reply_text("Game is starting! Use /join to participate. You have 1.5 minutes to join.")
            context.job_queue.run_once(remind_join, 60, chat_id=update.message.chat_id)
            context.job_queue.run_once(check_start_game, 90, chat_id=update.message.chat_id)
        else:
            await update.message.reply_text("Please interact with the bot in private chat first.")

async def remind_join(context: CallbackContext) -> None:
    await context.bot.send_message(context.job.chat_id, text="30 seconds left to join the game! Use /join to participate.")

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if user.id not in players and context.user_data.get('interacted'):
        players.append(user.id)
        await update.message.reply_text(f"{user.first_name} joined the game!")
        if len(players) == 4:
            await start_game(context.job.chat_id, context)

async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    if user.id in players:
        players.remove(user.id)
        await update.message.reply_text(f"{user.first_name} left the game. The game is ending.")
        await announce_results(context)
        reset_game()

async def check_start_game(context: CallbackContext) -> None:
    if len(players) < 4:
        await context.bot.send_message(context.job.chat_id, text="Not enough players joined. The game is ending.")
        reset_game()
    else:
        await start_game(context.job.chat_id, context)

async def start_game(chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    global current_round, mantri_id
    current_round += 1
    if current_round > rounds:
        await announce_results(context)
        reset_game()
        return
    
    await context.bot.send_message(chat_id, text=f"Round {current_round} is starting!")
    await assign_roles(context)
    await context.bot.send_message(chat_id, text="Mantri, please guess who the Chor is by using /guess <player_name>")
    
async def assign_roles(context: ContextTypes.DEFAULT_TYPE) -> None:
    global mantri_id
    random.shuffle(players)
    roles_assigned = dict(zip(players, roles))
    for player_id, role in roles_assigned.items():
        await context.bot.send_message(player_id, text=f"Your role: {role}")
        if role == "Raja":
            scores[player_id] = scores.get(player_id, 0) + 1000
        elif role == "Sipahi":
            scores[player_id] = scores.get(player_id, 0) + 100
        elif role == "Mantri":
            mantri_id = player_id
            scores[player_id] = scores.get(player_id, 0) + 500

async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global mantri_id
    user = update.message.from_user
    if user.id == mantri_id:
        try:
            guessed_player_name = context.args[0]
            guessed_player_id = next(player_id for player_id in players if (await context.bot.get_chat(player_id)).first_name == guessed_player_name)
            actual_chor_id = next(player_id for player_id, role in zip(players, roles) if role == "Chor")
            
            if guessed_player_id == actual_chor_id:
                await update.message.reply_text(f"Correct guess! {guessed_player_name} is the Chor.")
            else:
                await update.message.reply_text(f"Wrong guess! {guessed_player_name} is not the Chor. {(await context.bot.get_chat(actual_chor_id)).first_name} is the actual Chor.")
                scores[mantri_id] -= 500
        except (IndexError, StopIteration):
            await update.message.reply_text("Invalid guess. Please use /guess <player_name>")
        finally:
            await end_round(context)
    else:
        await update.message.reply_text("You are not the Mantri. You cannot make a guess.")

async def end_round(context: ContextTypes.DEFAULT_TYPE) -> None:
    global current_round
    chat_id = context.job.chat_id
    await context.bot.send_message(chat_id, text=f"Round {current_round} ended! Current scores:")
    for player_id in players:
        user = await context.bot.get_chat(player_id)
        await context.bot.send_message(chat_id, text=f"{user.first_name}: {scores[player_id]} points")
    if current_round < rounds:
        await start_game(chat_id, context)
    else:
        await announce_results(context)
        reset_game()

async def announce_results(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.chat_id
    await context.bot.send_message(chat_id, text="Game over! Final scores:")
    for player_id in players:
        user = await context.bot.get_chat(player_id)
        await context.bot.send_message(chat_id, text=f"{user.first_name}: {scores[player_id]} points")
    winner = max(scores, key=scores.get)
    winner_user = await context.bot.get_chat(winner)
    await context.bot.send_message(chat_id, text=f"The winner is {winner_user.first_name} with {scores[winner]} points!")

def reset_game() -> None:
    global players, scores, current_round, mantri_id
    players = []
    scores = {}
    current_round = 0
    mantri_id = None

def main() -> None:
    application = Application.builder().token().build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("startgame", startgame))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("leave", leave))
    application.add_handler(CommandHandler("guess", guess))
    
    application.run_polling()

if __name__ == '__main__':
    main()
