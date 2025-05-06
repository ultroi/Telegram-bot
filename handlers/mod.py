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
    get_user_achievements
)
from datetime import datetime, timedelta
import asyncio

# Stats command
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's game statistics."""
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
    
    # Calculate win rate percentages
    total_games = stats['total_games']
    win_rate = stats['win_rate']
    challenge_games = stats['challenge_games']
    challenge_win_rate = round((stats['challenge_wins'] / challenge_games) * 100, 1) if challenge_games > 0 else 0
    
    # Format the stats message with emojis and good formatting
    stats_message = (
        f"📊 <b>Stats for {display_name}</b> 📊\n\n"
        f"<b>Level:</b> {stats['level']} ({stats['experience_points']} XP)\n"
        f"<b>Rank:</b> #{stats['leaderboard_rank']} on the leaderboard\n\n"
        
        f"🎮 <b>Overall Stats:</b>\n"
        f"Games Played: {total_games}\n"
        f"Wins: {stats['total_wins']} ({win_rate}%)\n"
        f"Losses: {stats['total_losses']}\n"
        f"Ties: {stats['total_ties']}\n\n"
        
        f"🏆 <b>Challenge Games:</b>\n"
        f"Challenges: {challenge_games}\n"
        f"Wins: {stats['challenge_wins']} ({challenge_win_rate}%)\n"
        f"Losses: {stats['challenge_losses']}\n\n"
        
        f"🎲 <b>Move Preferences:</b>\n"
        f"🪨 Rock: {stats['rock_played']} times\n"
        f"📄 Paper: {stats['paper_played']} times\n"
        f"✂️ Scissor: {stats['scissor_played']} times\n"
    )
    
    if stats['favorite_move']:
        favorite_move_emoji = {"rock": "🪨", "paper": "📄", "scissor": "✂️"}[stats['favorite_move']]
        stats_message += f"Favorite Move: {favorite_move_emoji} {stats['favorite_move'].capitalize()}\n\n"
    
    # Add achievements button
    keyboard = [
        [InlineKeyboardButton("🏅 View Achievements", callback_data=f"achievements_{user.id}")]
    ]
    
    await update.message.reply_text(
        stats_message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Achievements callback
async def achievements_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user achievements."""
    query = update.callback_query
    await query.answer()
    
    _, user_id = query.data.split("_")
    user_id = int(user_id)
    
    # Get user achievements
    achievements = await get_user_achievements(user_id)
    
    if not achievements:
        await query.edit_message_text(
            "🏅 No achievements unlocked yet!\n\nKeep playing to earn achievements!",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Format achievements message
    achievements_message = "🏅 <b>Your Achievements</b> 🏅\n\n"
    
    for achievement in achievements:
        achievement_icon = {
            "perfect_victory": "🌟",
            "first_win": "🎉",
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
    
    await query.edit_message_text(
        achievements_message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Back to stats callback
async def back_to_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to stats view from achievements."""
    query = update.callback_query
    await query.answer()
    
    _, _, user_id = query.data.split("_")
    user_id = int(user_id)
    
    # Get user stats again
    stats = await get_user_stats(user_id)
    
    if not stats:
        await query.edit_message_text("No statistics found. Play some games first!")
        return
    
    # Re-create the stats message (simplified version)
    stats_message = (
        f"📊 <b>Stats for {stats['first_name']}</b> 📊\n\n"
        f"<b>Level:</b> {stats['level']} ({stats['experience_points']} XP)\n"
        f"<b>Rank:</b> #{stats['leaderboard_rank']}\n\n"
        f"Games: {stats['total_games']} | Wins: {stats['total_wins']} ({stats['win_rate']}%)\n"
        f"Challenges: {stats['challenge_games']} | Wins: {stats['challenge_wins']}\n"
    )
    
    # Add achievements button again
    keyboard = [
        [InlineKeyboardButton("🏅 View Achievements", callback_data=f"achievements_{user_id}")]
    ]
    
    await query.edit_message_text(
        stats_message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Leaderboard command
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the game leaderboard."""
    user = update.message.from_user
    
    # Update user activity
    await update_user_activity(user.id, user.first_name, user.last_name, user.username)
    
    # Determine which leaderboard to show
    category = "wins"  # Default category
    if context.args:
        arg = context.args[0].lower()
        if arg in ["wins", "challenge", "level", "games"]:
            if arg == "challenge":
                category = "challenge_wins"
            else:
                category = arg
    
    # Get leaderboard data
    leaders = await get_leaderboard(category, 10)
    
    if not leaders:
        await update.message.reply_text("No players found on the leaderboard yet!")
        return
    
    # Create leaderboard message with formatting and emojis
    category_titles = {
        "wins": "🏆 Most Wins",
        "challenge_wins": "🎯 Challenge Champions",
        "level": "⭐ Highest Levels",
        "games": "🎮 Most Active Players"
    }
    
    leaderboard_message = f"📊 <b>{category_titles[category]} Leaderboard</b> 📊\n\n"
    
    # Medals for top 3
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
    
    # Add buttons to switch between leaderboard categories
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
    
    await update.message.reply_text(
        leaderboard_message,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Leaderboard callback for switching categories
async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, category = query.data.split("_", 1)
    
    # Get leaderboard data for the selected category
    leaders = await get_leaderboard(category, 10)
    
    if not leaders:
        await query.edit_message_text("No players found on the leaderboard yet!")
        return
    
    # Re-create leaderboard message for the new category
    category_titles = {
        "wins": "🏆 Most Wins",
        "challenge_wins": "🎯 Challenge Champions",
        "level": "⭐ Highest Levels",
        "games": "🎮 Most Active Players"
    }
    
    leaderboard_message = f"📊 <b>{category_titles[category]} Leaderboard</b> 📊\n\n"
    
    # Medals for top 3
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
    
    # Keep the same buttons
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

# Admin commands
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view system statistics."""
    # Check if user is admin
    admin_ids = [5956598856]  # Add admin IDs here
    if update.message.from_user.id not in admin_ids:
        await update.message.reply_text("⛔ You are not authorized to use this command.")
        return
    
    # Get system stats
    stats = await get_system_stats()
    
    stats_message = (
        f"🤖 <b>System Statistics</b> 🤖\n\n"
        f"👥 <b>Users:</b> {stats['total_users']}\n"
        f"👥 <b>Active Users (7d):</b> {stats['active_users']}\n"
        f"👥 <b>Groups:</b> {stats['total_groups']}\n"
        f"🎮 <b>Total Games:</b> {stats['total_games']}\n"
    )
    
    await update.message.reply_text(
        stats_message,
        parse_mode=ParseMode.HTML
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to broadcast a message to all users."""
    # Check if user is admin
    admin_ids = [5956598856]  # Add admin IDs here
    if update.message.from_user.id not in admin_ids:
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
    """Confirm and execute the broadcast."""
    admin_ids = [5956598856]  # Add admin IDs here

    if update.message.from_user.id not in admin_ids:
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
