from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
import random
import logging
from database.connection import ensure_tables_exist, update_user_activity, get_user_stats, get_leaderboard, get_user_achievements, update_stats, record_game, update_bot_stats, get_user_bot_stats, record_round, add_achievement

#Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interactive start command with UI for the Rock Paper Scissors bot."""
    user = update.message.from_user

    # Ensure database tables exist
    try:
        await ensure_tables_exist()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        await update.message.reply_text("Error initializing database. Please try again later.")
        return
    
    # Update user activity in database
    try:
        await update_user_activity(user.id, user.first_name, user.last_name, user.username)
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")
    
    # Create a welcome message with interactive buttons
    welcome_text = (
        f"👋 <b>Welcome {user.first_name} to Rock Paper Scissors Challenge!</b> 👋\n\n"
        "🎮 <i>Challenge your friends to epic battles and see who's the ultimate champion!</i>\n\n"
        "🪨 📄 ✂️ <b>How to play:</b>\n"
        "1. Use /challenge in a group (reply to someone's message)\n"
        "2. Wait for them to accept\n"
        "3. Make your move when it's your turn\n"
        "4. Best of 1-10 rounds wins!\n\n"
        "🏆 <b>Features:</b>\n"
        "- Track your win/loss stats\n"
        "- Earn achievements\n"
        "- Level up as you play\n"
        "- Rematch option after games"
    )
    
    # Create interactive buttons
    keyboard = [
        [
            InlineKeyboardButton("📖 How to Play", callback_data="help"),
            InlineKeyboardButton("📊 My Stats", callback_data="stats")
        ],
        [
            InlineKeyboardButton("🎮 Quick Game (vs Bot)", callback_data="quick_game"),
            InlineKeyboardButton("👥 Challenge Friends", switch_inline_query="")
        ],
        [
            InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
            InlineKeyboardButton("🌟 Achievements", callback_data="achievements")
        ]
    ]
    
    # Send the message with photo and buttons
    try:
        await update.message.reply_photo(
            photo="https://files.catbox.moe/qrswmu.jpg",
            caption=welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error sending start message: {e}")
        await update.message.reply_text("Error displaying start menu. Please try again.")

async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from the start command buttons."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    action = query.data
    logger.info(f"Callback received: {action} from user {user.id}")
    
    if action == "help":
        help_text = (
            "🪨📄✂️ <b>Rock Paper Scissors Challenge - How to Play</b> ✂️📄🪨\n\n"
            "1. <b>Challenge a friend</b> in a group chat:\n"
            "   - Reply to their message with <code>/challenge</code>\n"
            "   - Or <code>/challenge 3</code> for best of 3 rounds\n\n"
            "2. <b>They'll get a challenge request</b> to accept or decline\n\n"
            "3. <b>When accepted</b>, you'll take turns making moves:\n"
            "   - 🪨 Rock\n"
            "   - 📄 Paper\n"
            "   - ✂️ Scissors\n\n"
            "4. <b>Winner</b> is determined by standard rules:\n"
            "   - Rock crushes Scissors\n"
            "   - Scissors cut Paper\n"
            "   - Paper covers Rock\n\n"
            "🏆 <b>Stats & Achievements</b> are tracked for all players!"
        )
        
        await query.edit_message_caption(
            caption=help_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]),
            parse_mode=ParseMode.HTML
        )
    
    elif action == "stats":
        try:
            stats = await get_user_stats(user.id)
            if not stats:
                stats_text = "No stats available yet! Play some games to start tracking your progress!"
            else:
                stats_text = (
                    f"📊 <b>{user.first_name}'s Game Stats</b> 📊\n\n"
                    f"🏆 <b>Wins:</b> {stats['total_wins']}\n"
                    f"😞 <b>Losses:</b> {stats['total_losses']}\n"
                    f"🤝 <b>Ties:</b> {stats['total_ties']}\n"
                    f"📈 <b>Win Rate:</b> {stats['win_rate']}%\n\n"
                    f"🎚️ <b>Level:</b> {stats['level']}\n"
                    f"✨ <b>XP:</b> {stats['experience_points']}\n\n"
                    f"🌟 <b>Favorite Move:</b> {stats['favorite_move'] or 'None'}\n"
                    f"🏅 <b>Leaderboard Rank:</b> #{stats['leaderboard_rank']}"
                )
            
            await query.edit_message_caption(
                caption=stats_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")],
                    [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")]
                ]),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error fetching stats for user {user.id}: {e}")
            await query.edit_message_caption(
                caption="Error fetching stats. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
            )
    
    elif action == "quick_game":
        try:
            await start_bot_game(query, context)
        except Exception as e:
            logger.error(f"Error starting bot game for user {user.id}: {e}")
            await query.edit_message_caption(
                caption="Error starting quick game. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
            )
    
    elif action == "leaderboard":
        try:
            leaderboard = await get_leaderboard(category='wins', limit=10)
            leaderboard_text = "🏆 <b>Top Players</b> 🏆\n\n"
            
            if not leaderboard:
                leaderboard_text += "No players on the leaderboard yet!"
            else:
                for i, player in enumerate(leaderboard, 1):
                    name = f"{player['first_name']} {player['last_name'] or ''}".strip()
                    leaderboard_text += f"{i}. {name} - {player['total_wins']} wins (Lvl {player['level']})\n"
            
            leaderboard_text += "\n<i>Play more to climb the ranks!</i>"
            
            await query.edit_message_caption(
                caption=leaderboard_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error fetching leaderboard: {e}")
            await query.edit_message_caption(
                caption="Error fetching leaderboard. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
            )
    
    elif action == "achievements":
        try:
            achievements = await get_user_achievements(user.id)
            achievements_text = f"🌟 <b>{user.first_name}'s Achievements</b> 🌟\n\n"
            
            if not achievements:
                achievements_text += "No achievements yet! Keep playing to earn some!"
            else:
                for ach in achievements:
                    achievements_text += f"✅ <b>{ach['achievement_type']}</b>\n<i>{ach['description']}</i>\n"
                    achievements_text += f"<small>Earned: {ach['achievement_date']}</small>\n\n"
            
            await query.edit_message_caption(
                caption=achievements_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error fetching achievements for user {user.id}: {e}")
            await query.edit_message_caption(
                caption="Error fetching achievements. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
            )
    
    elif action == "back_to_start":
        welcome_text = (
            f"👋 <b>Welcome {user.first_name} to Rock Paper Scissors Challenge!</b> 👋\n\n"
            "🎮 <i>Challenge your friends to epic battles and see who's the ultimate champion!</i>\n\n"
            "🪨 📄 ✂️ <b>How to play:</b>\n"
            "1. Use /challenge in a group (reply to someone's message)\n"
            "2. Wait for them to accept\n"
            "3. Make your move when it's your turn\n"
            "4. Best of 1-10 rounds wins!\n\n"
            "🏆 <b>Features:</b>\n"
            "- Track your win/loss stats\n"
            "- Earn achievements\n"
            "- Level up as you play\n"
            "- Rematch option after games"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("📖 How to Play", callback_data="help"),
                InlineKeyboardButton("📊 My Stats", callback_data="stats")
            ],
            [
                InlineKeyboardButton("🎮 Quick Game (vs Bot)", callback_data="quick_game"),
                InlineKeyboardButton("👥 Challenge Friends", switch_inline_query="")
            ],
            [
                InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
                InlineKeyboardButton("🌟 Achievements", callback_data="achievements")
            ]
        ]
        
        try:
            await query.edit_message_caption(
                caption=welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error returning to start menu for user {user.id}: {e}")
            await query.edit_message_caption(
                caption="Error returning to main menu. Please try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
            )

async def start_bot_game(query, context):
    """Start a quick game against the bot."""
    user = query.from_user
    bot_user = await context.bot.get_me()
    
    # Store game state
    context.user_data['bot_game'] = {
        'player_id': user.id,
        'bot_id': bot_user.id,
        'round': 1
    }
    
    # Create a game against the bot
    keyboard = [
        [
            InlineKeyboardButton("🪨 Rock", callback_data=f"bot_move_rock"),
            InlineKeyboardButton("📄 Paper", callback_data=f"bot_move_paper"),
            InlineKeyboardButton("✂️ Scissor", callback_data=f"bot_move_scissor")
        ]
    ]
    
    try:
        await query.edit_message_caption(
            caption=f"🎮 <b>Quick Game vs {bot_user.first_name}</b> 🎮\n\n"
                   f"Make your move, {user.first_name}!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error starting bot game UI for user {user.id}: {e}")
        await query.edit_message_caption(
            caption="Error starting game. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
        )

async def handle_bot_move(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle player's move in a bot game."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    player_move = query.data.split('_')[-1]  # Get move from callback data (rock/paper/scissor)
    logger.info(f"Bot game move by user {user.id}: {player_move}")
    
    # Generate bot's move
    moves = ['rock', 'paper', 'scissor']
    bot_move = random.choice(moves)
    
    # Determine winner
    winner_id = None
    result_text = f"🎮 <b>Round Result</b> 🎮\n\n"
    result_text += f"{user.first_name}: {player_move.capitalize()} 🆚 Bot: {bot_move.capitalize()}\n\n"
    
    if player_move == bot_move:
        result = 'tie'
        result_text += "🤝 It's a tie!"
        winner_id = None
    elif (
        (player_move == 'rock' and bot_move == 'scissor') or
        (player_move == 'paper' and bot_move == 'rock') or
        (player_move == 'scissor' and bot_move == 'paper')
    ):
        result = 'win'
        result_text += f"🏆 {user.first_name} wins!"
        winner_id = user.id
    else:
        result = 'loss'
        result_text += "😞 Bot wins!"
        winner_id = context.bot.id
    
    # Record game in database
    try:
        game_id = await record_game(
            player1_id=user.id,
            player2_id=context.bot.id,
            winner_id=winner_id,
            game_type='bot',  # Use 'bot' game type
            rounds=1
        )
        
        # Record round details
        await record_round(
            game_id=game_id,
            round_number=1,
            player1_move=player_move,
            player2_move=bot_move,
            winner_id=winner_id
        )
        
        # Update player bot stats
        await update_bot_stats(user.id, result, player_move)
        
        # Check for achievements
        stats = await get_user_bot_stats(user.id)  # New function to get bot stats
        if stats['total_games'] == 1:
            await add_achievement(user.id, "First Bot Game", "Played your first game against the bot!")
        if result == 'win' and stats['total_wins'] == 1:
            await add_achievement(user.id, "First Bot Win", "Won your first game against the bot!")
    
    except Exception as e:
        logger.error(f"Error processing bot game for user {user.id}: {e}")
        result_text += "\n\n⚠️ Error saving game results. Please try again."
    
    keyboard = [
        [InlineKeyboardButton("🔄 Play Again", callback_data="quick_game")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back_to_start")]
    ]
    
    try:
        await query.edit_message_caption(
            caption=result_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Error updating bot game result for user {user.id}: {e}")
        await query.edit_message_caption(
            caption="Error displaying game result. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]])
        )
