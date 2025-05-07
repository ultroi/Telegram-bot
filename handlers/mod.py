from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database.connection import (
    get_db_connection, 
    update_user_activity, 
    get_user_stats, 
    get_leaderboard,
    get_system_stats,
    get_broadcast_users,
    get_user_achievements,
    get_group_leaderboard,
    is_admin
)
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

# Stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's overall game statistics, including challenge and bot games."""
    user = update.message.from_user
    
    # Update user activity
    await update_user_activity(user.id, user.first_name, user.last_name, user.username)
    
    # Check if requesting stats for another user
    target_user = None
    if context.args and update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please either mention a username or reply to a message, not both.")
        return
    elif context.args:
        # Attempt to find user by username
        username = context.args[0].lstrip('@')
        async with get_db_connection() as conn:
            async with conn.execute('SELECT user_id FROM users WHERE username = ?', (username,)) as cursor:
                user_row = await cursor.fetchone()
                if user_row:
                    target_user_id = user_row['user_id']
                    stats = await get_user_stats(target_user_id)
                else:
                    await update.message.reply_text(f"⚠️ User @{username} not found in the database.")
                    return
    elif update.message.reply_to_message:
        # Get stats for the replied-to user
        target_user = update.message.reply_to_message.from_user
        stats = await get_user_stats(target_user.id)
    else:
        # Get stats for the requesting user
        stats = await get_user_stats(user.id)
        
    if not stats:
        await update.message.reply_text("No statistics found. Play some games first!")
        return
    
    # Format the stats message
    display_name = target_user.first_name if target_user else stats['first_name']
    
    # Calculate overall stats
    overall_games = stats['total_games'] + stats['bot_games']
    overall_wins = stats['total_wins'] + stats['bot_wins']
    overall_losses = stats['total_losses'] + stats['bot_losses']
    overall_ties = stats['total_ties'] + stats['bot_ties']
    overall_win_rate = round((overall_wins / overall_games) * 100, 1) if overall_games > 0 else 0
    
    # Calculate challenge-specific win rate
    challenge_games = stats['challenge_games']
    challenge_win_rate = round((stats['challenge_wins'] / challenge_games) * 100, 1) if challenge_games > 0 else 0
    
    # Calculate bot-specific win rate
    bot_games = stats['bot_games']
    bot_win_rate = round((stats['bot_wins'] / bot_games) * 100, 1) if bot_games > 0 else 0
    
    # Calculate total move preferences
    total_rock = stats['rock_played'] + stats['bot_rock_played']
    total_paper = stats['paper_played'] + stats['bot_paper_played']
    total_scissor = stats['scissor_played'] + stats['bot_scissor_played']
    
    # Determine overall favorite move
    moves = {
        'rock': total_rock,
        'paper': total_paper,
        'scissor': total_scissor
    }
    favorite_move = max(moves, key=moves.get) if sum(moves.values()) > 0 else None
    
    # Format the stats message with emojis and clear sections
    stats_message = (
        f"📊 <b>Stats for {display_name}</b> 📊\n\n"
        f"<b>Level:</b> {stats['level']} ({stats['experience_points']} XP)\n"
        f"<b>Rank:</b> #{stats['leaderboard_rank']} on the leaderboard\n\n"
        
        f"🎮 <b>Overall Stats:</b>\n"
        f"Games Played: {overall_games}\n"
        f"Wins: {overall_wins} ({overall_win_rate}%)\n"
        f"Losses: {overall_losses}\n"
        f"Ties: {overall_ties}\n\n"
        
        f"🏆 <b>Challenge Mode Stats:</b>\n"
        f"Games: {challenge_games}\n"
        f"Wins: {stats['challenge_wins']} ({challenge_win_rate}%)\n"
        f"Losses: {stats['challenge_losses']}\n"
        f"Ties: {stats['total_ties']}\n\n"
        
        f"🤖 <b>Bot Game Stats:</b>\n"
        f"Games: {bot_games}\n"
        f"Wins: {stats['bot_wins']} ({bot_win_rate}%)\n"
        f"Losses: {stats['bot_losses']}\n"
        f"Ties: {stats['bot_ties']}\n\n"
        
        f"🎲 <b>Move Preferences:</b>\n"
        f"🪨 Rock: {total_rock} times\n"
        f"📄 Paper: {total_paper} times\n"
        f"✂️ Scissor: {total_scissor} times\n"
    )
    
    if favorite_move:
        favorite_move_emoji = {"rock": "🪨", "paper": "📄", "scissor": "✂️"}[favorite_move]
        stats_message += f"Favorite Move: {favorite_move_emoji} {favorite_move.capitalize()}\n\n"
    
    # Add achievements button
    keyboard = [
        [InlineKeyboardButton("🏅 View Achievements", callback_data=f"achievements_{stats['user_id'] if target_user else user.id}")]
    ]
    
    try:
        await update.message.reply_text(
            stats_message,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error displaying stats for user {user.id}: {e}")
        await update.message.reply_text("⚠️ Error displaying stats. Please try again.")

async def achievements_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user achievements for both challenge and bot games."""
    query = update.callback_query
    await query.answer()
    
    _, user_id = query.data.split("_")
    user_id = int(user_id)
    
    # Get user achievements
    achievements = await get_user_achievements(user_id)
    
    if not achievements:
        await query.edit_message_text(
            "🏅 No achievements unlocked yet!\n\nKeep playing challenge or bot games to earn achievements!",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Format achievements message
    achievements_message = "🏅 <b>Your Achievements</b> 🏅\n\n"
    
    for achievement in achievements:
        achievement_icon = {
            "perfect_victory": "🌟",
            "first_win": "🎉",
            "first_bot_game": "🤖",
            "first_bot_win": "🎮",
            "veteran": "🏆",
            "comeback": "💪",
            "lucky": "🍀"
        }.get(achievement['achievement_type'], "🎖️")
        
        achievements_message += f"{achievement_icon} <b>{achievement['achievement_type'].replace('_', ' ').title()}</b>\n"
        achievements_message += f"<i>{achievement['description']}</i>\n"
        achievements_message += f"Earned on: {achievement['achievement_date'].split('T')[0]}\n\n"
    
    # Add back button
    keyboard = [
        [InlineKeyboardButton("◀️ Back to Stats", callback_data=f"back_to_stats_{user_id}")]
    ]
    
    try:
        await query.edit_message_text(
            achievements_message,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error displaying achievements for user {user_id}: {e}")
        await query.edit_message_text(
            "⚠️ Error displaying achievements. Please try again.",
            parse_mode=ParseMode.HTML
        )

async def back_to_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the back to stats button."""
    query = update.callback_query
    await query.answer()
    
    _, user_id = query.data.split("_")
    user_id = int(user_id)
    
    # Get user stats
    stats = await get_user_stats(user_id)
    
    if not stats:
        await query.edit_message_text("No statistics found. Play some games first!")
        return
    
    # Calculate overall stats
    overall_games = stats['total_games'] + stats['bot_games']
    overall_wins = stats['total_wins'] + stats['bot_wins']
    overall_losses = stats['total_losses'] + stats['bot_losses']
    overall_ties = stats['total_ties'] + stats['bot_ties']
    overall_win_rate = round((overall_wins / overall_games) * 100, 1) if overall_games > 0 else 0
    
    # Calculate challenge-specific win rate
    challenge_games = stats['challenge_games']
    challenge_win_rate = round((stats['challenge_wins'] / challenge_games) * 100, 1) if challenge_games > 0 else 0
    
    # Calculate bot-specific win rate
    bot_games = stats['bot_games']
    bot_win_rate = round((stats['bot_wins'] / bot_games) * 100, 1) if bot_games > 0 else 0
    
    # Calculate total move preferences
    total_rock = stats['rock_played'] + stats['bot_rock_played']
    total_paper = stats['paper_played'] + stats['bot_paper_played']
    total_scissor = stats['scissor_played'] + stats['bot_scissor_played']
    
    # Determine overall favorite move
    moves = {
        'rock': total_rock,
        'paper': total_paper,
        'scissor': total_scissor
    }
    favorite_move = max(moves, key=moves.get) if sum(moves.values()) > 0 else None
    
    # Format the stats message
    stats_message = (
        f"📊 <b>Stats for {stats['first_name']}</b> 📊\n\n"
        f"<b>Level:</b> {stats['level']} ({stats['experience_points']} XP)\n"
        f"<b>Rank:</b> #{stats['leaderboard_rank']} on the leaderboard\n\n"
        
        f"🎮 <b>Overall Stats:</b>\n"
        f"Games Played: {overall_games}\n"
        f"Wins: {overall_wins} ({overall_win_rate}%)\n"
        f"Losses: {overall_losses}\n"
        f"Ties: {overall_ties}\n\n"
        
        f"🏆 <b>Challenge Mode Stats:</b>\n"
        f"Games: {challenge_games}\n"
        f"Wins: {stats['challenge_wins']} ({challenge_win_rate}%)\n"
        f"Losses: {stats['challenge_losses']}\n"
        f"Ties: {stats['total_ties']}\n\n"
        
        f"🤖 <b>Bot Game Stats:</b>\n"
        f"Games: {bot_games}\n"
        f"Wins: {stats['bot_wins']} ({bot_win_rate}%)\n"
        f"Losses: {stats['bot_losses']}\n"
        f"Ties: {stats['bot_ties']}\n\n"
        
        f"🎲 <b>Move Preferences:</b>\n"
        f"🪨 Rock: {total_rock} times\n"
        f"📄 Paper: {total_paper} times\n"
        f"✂️ Scissor: {total_scissor} times\n"
    )
    
    if favorite_move:
        favorite_move_emoji = {"rock": "🪨", "paper": "📄", "scissor": "✂️"}[favorite_move]
        stats_message += f"Favorite Move: {favorite_move_emoji} {favorite_move.capitalize()}\n\n"
    
    # Add achievements button
    keyboard = [
        [InlineKeyboardButton("🏅 View Achievements", callback_data=f"achievements_{user_id}")]
    ]
    
    try:
        await query.edit_message_text(
            stats_message,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error displaying stats for user {user_id}: {e}")
        await query.edit_message_text(
            "⚠️ Error displaying stats. Please try again.",
            parse_mode=ParseMode.HTML
        )

async def format_leaderboard(leaders: list, category: str, is_group: bool = False, group_id: int = None) -> tuple[str, InlineKeyboardMarkup]:
    """Format the leaderboard message and buttons."""
    if not leaders:
        return ("No players found on the leaderboard yet!", InlineKeyboardMarkup([]))
    
    category_titles = {
        "wins": "🏆 Most Wins",
        "challenge_wins": "🎯 Challenge Champions",
        "level": "⭐ Highest Levels",
        "games": "🎮 Most Active Players"
    }
    
    title = f"📊 <b>{category_titles[category]} {'Group' if is_group else 'Global'} Leaderboard</b> 📊\n\n"
    leaderboard_message = title
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, leader in enumerate(leaders):
        rank_display = medals[i] if i < 3 else f"{i+1}."
        name = f"{leader['first_name']} {leader['last_name'] or ''}".strip()
        
        if category == "wins":
            leaderboard_message += f"{rank_display} <b>{name}</b> - {leader['total_wins']} wins (Level {leader['level']})\n"
        elif category == "challenge_wins":
            leaderboard_message += f"{rank_display} <b>{name}</b> - {leader['challenge_wins']} challenge wins (Level {leader['level']})\n"
        elif category == "level":
            leaderboard_message += f"{rank_display} <b>{name}</b> - Level {leader['level']} ({leader['experience_points']} XP)\n"
        elif category == "games":
            leaderboard_message += f"{rank_display} <b>{name}</b> - {leader['total_games']} games played (Level {leader['level']})\n"
    
    # Create buttons
    prefix = "leaderboard_group_" if is_group else "leaderboard_"
    keyboard = [
        [
            InlineKeyboardButton("🏆 Wins", callback_data=f"{prefix}wins_{group_id or 0}"),
            InlineKeyboardButton("🎯 Challenges", callback_data=f"{prefix}challenge_wins_{group_id or 0}")
        ],
        [
            InlineKeyboardButton("⭐ Levels", callback_data=f"{prefix}level_{group_id or 0}"),
            InlineKeyboardButton("🎮 Most Active", callback_data=f"{prefix}games_{group_id or 0}")
        ]
    ]
    
    # Add toggle button
    if is_group:
        keyboard.append([InlineKeyboardButton("🌍 View Global Leaderboard", callback_data=f"leaderboard_switch_to_global_{category}_{group_id}")])
    elif group_id:
        keyboard.append([InlineKeyboardButton("🏠 Back to Group Leaderboard", callback_data=f"leaderboard_switch_to_group_{category}_{group_id}")])
    
    return leaderboard_message, InlineKeyboardMarkup(keyboard)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the game leaderboard (global in PM, group-specific in GC)."""
    user = update.message.from_user
    chat = update.effective_chat
    
    # Update user activity
    await update_user_activity(user.id, user.first_name, user.last_name, user.username)
    
    # Determine category
    category = "wins"
    if context.args:
        arg = context.args[0].lower()
        if arg in ["wins", "challenge", "level", "games"]:
            category = "challenge_wins" if arg == "challenge" else arg
    
    try:
        if chat.type == "private":
            # Show global leaderboard in PM
            leaders = await get_leaderboard(category, 10)
            message, keyboard = await format_leaderboard(leaders, category)
        else:
            # Show group leaderboard in group chat
            group_id = chat.id
            leaders = await get_group_leaderboard(group_id, category, 10)
            message, keyboard = await format_leaderboard(leaders, category, is_group=True, group_id=group_id)
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error displaying leaderboard for user {user.id} in chat {chat.id}: {e}")
        await update.message.reply_text("⚠️ Error displaying leaderboard. Please try again.")


async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle leaderboard category switches and global/group toggling."""
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    action = data[0]

    try:
        if action == "leaderboard" or action == "leaderboard_group":
            is_group = action == "leaderboard_group"
            category = data[1]
            group_id = int(data[2]) if data[2] != "0" else None

            if category not in ("wins", "challenge_wins", "level", "games"):
                await query.edit_message_text("⚠️ Invalid leaderboard category!")
                return

            if is_group:
                leaders = await get_group_leaderboard(group_id, category, 10)
                message, keyboard = await format_leaderboard(leaders, category, is_group=True, group_id=group_id)
            else:
                leaders = await get_leaderboard(category, 10)
                message, keyboard = await format_leaderboard(leaders, category, group_id=group_id)

        elif action == "leaderboard_switch_to_global":
            category = data[1]
            group_id = int(data[2])

            if category not in ("wins", "challenge_wins", "level", "games"):
                await query.edit_message_text("⚠️ Invalid leaderboard category!")
                return

            leaders = await get_leaderboard(category, 10)
            message, keyboard = await format_leaderboard(leaders, category, group_id=group_id)

        elif action == "leaderboard_switch_to_group":
            category = data[1]
            group_id = int(data[2])

            if category not in ("wins", "challenge_wins", "level", "games"):
                await query.edit_message_text("⚠️ Invalid leaderboard category!")
                return

            leaders = await get_group_leaderboard(group_id, category, 10)
            message, keyboard = await format_leaderboard(leaders, category, is_group=True, group_id=group_id)

        # Try editing the message text; if it fails (e.g., captioned image), try editing caption
        try:
            await query.edit_message_text(
                text=message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        except Exception:
            await query.edit_message_caption(
                caption=message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

    except Exception as e:
        logger.error(f"Error handling leaderboard callback for user {query.from_user.id}: {e}")
        await query.edit_message_text("⚠️ An error occurred while switching leaderboard. Please try again.")


# Admin commands
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # Define user_id
    # Check if user is admin
    if not await is_admin(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    # Get system stats
    stats_data = await get_system_stats()

    # Handle None response
    if stats_data is None:
        await update.message.reply_text("⚠️ Failed to fetch system stats.")
        return

    # Build and send stats message
    stats_message = (
        f"🤖 <b>System Statistics</b> 🤖\n\n"
        f"👥 <b>Users:</b> {stats_data['total_users']}\n"
        f"👥 <b>Active Users (7d):</b> {stats_data['active_users']}\n"
        f"👥 <b>Groups:</b> {stats_data['total_groups']}\n"
        f"🎮 <b>Total Games:</b> {stats_data['total_games']}\n"
    )
    await update.message.reply_text(
        stats_message,
        parse_mode=ParseMode.HTML
    )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # Define user_id
    # Check if user is admin
    if not await is_admin(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return
    
    # Check if message is provided
    if not context.args:
        await update.message.reply_text("⚠️ Please provide a message to broadcast.")
        return
    
    # Get the broadcast message
    message = " ".join(context.args)
    
    # Get all user IDs
    user_ids = await get_broadcast_users()
    
    if not user_ids:
        await update.message.reply_text("No users found to broadcast to.")
        return
    
    # Confirm broadcast
    await update.message.reply_text(
        f"📢 Broadcasting message to {len(user_ids)} users:\n\n"
        f"{message}\n\n"
        f"Send /confirm_broadcast to proceed."
    )
    
    # Store broadcast info for confirmation
    context.user_data["broadcast_message"] = message
    context.user_data["broadcast_users"] = user_ids

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # Define user_id
    # Check if user is admin
    if not await is_admin(user_id):
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return

    if "broadcast_message" not in context.user_data or "broadcast_users" not in context.user_data:
        await update.message.reply_text("⚠️ No pending broadcast. Use /broadcast first.")
        return

    message = context.user_data["broadcast_message"]
    user_ids = context.user_data["broadcast_users"]

    progress_msg = await update.message.reply_text("📢 Broadcasting in progress... 0%")

    successful = 0
    failed = 0

    for i, user_id in enumerate(user_ids):
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 <b>Broadcast Message from Trihand Bot</b> 📢\n\n{message}",
                parse_mode=ParseMode.HTML,
            )
            successful += 1
        except:
            failed += 1

        # Update progress every 10 users or last
        if (i + 1) % 10 == 0 or i == len(user_ids) - 1:
            percent = int(((i + 1) / len(user_ids)) * 100)
            await progress_msg.edit_text(f"📢 Broadcasting in progress... {percent}%")

    await progress_msg.edit_text(
        f"✅ Broadcast complete!\n\n✅ Successful: {successful}\n❌ Failed: {failed}"
    )


async def show_leaderboard(query, leaders, category):
    """Displays the leaderboard based on the selected category."""
    leaderboard_message = "🏅 <b>Leaderboard</b> 🏅\n\n"

    for rank, leader in enumerate(leaders, start=1):
        rank_display = f"#{rank}"
        name = leader.get("name", "Unknown")

        if category == "wins":
            leaderboard_message += f"{rank_display} <b>{name}</b> - {leader['total_wins']} wins (Level {leader['level']})\n"
        elif category == "challenge_wins":
            leaderboard_message += f"{rank_display} <b>{name}</b> - {leader['challenge_wins']} challenge wins (Level {leader['level']})\n"
        elif category == "level":
            leaderboard_message += f"{rank_display} <b>{name}</b> - Level {leader['level']} ({leader['experience_points']} XP)\n"
        elif category == "games":
            leaderboard_message += f"{rank_display} <b>{name}</b> - {leader['total_games']} games played (Level {leader['level']})\n"

    keyboard = [
        [
            InlineKeyboardButton("🏆 Wins", callback_data="leaderboard_wins"),
            InlineKeyboardButton("🎯 Challenges", callback_data="leaderboard_challenge_wins")
        ],
        [
            InlineKeyboardButton("⭐ Levels", callback_data="leaderboard_level"),
            InlineKeyboardButton("🎮 Most Active", callback_data="leaderboard_games")
        ]
    ]

    await query.edit_message_text(
        leaderboard_message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
