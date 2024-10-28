from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Help command: Display available commands
async def help_command(client, message):
    help_message = (
        "Help Menu:\n\n"
        "Here are the available commands:\n"
        "/start - Start the bot and choose a mode\n"
        "/ban <user_id> - Ban a user (Developer only)\n"
        "/unban <user_id> - Unban a user (Developer only)\n"
        "/dev_stats - Check developer stats (Developer only)\n"
        "/help - Show this help message\n"
    )

    keyboard = [
        [InlineKeyboardButton("Developer Commands", callback_data='dev_commands')],
        [InlineKeyboardButton("Back to Menu", callback_data='main_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(help_message, reply_markup=reply_markup)

# Display developer commands
async def show_dev_commands(client, message):
    dev_commands_message = (
        "Developer Commands:\n\n"
        "/ban <user_id> - Ban a user from using the bot\n"
        "/unban <user_id> - Unban a user\n"
        "/dev_stats - Check user and game stats\n"
        "Use these commands responsibly!"
    )

    await message.reply_text(dev_commands_message)