from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
import random
import logging
from database.connection import (
ensure_tables_exist,
update_user_activity,
get_user_stats,
get_user_bot_stats,
get_leaderboard,
get_user_achievements,
update_stats,
record_game,
update_bot_stats,
record_round,
add_achievement
)

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
        f"👋 <b>Welcome {user.first_name} to <b>Trihand GameBot</b>!</b> 👋\n\n"
        "Trihand is a fast-paced, multiplayer version of the classic <b>Rock 🪨, Paper 📄, Scissors ✂️</b> game – now with up to <b>10 intense rounds</b> per match!\n\n"
        "🎮 <i>Challenge your friends, outsmart their moves, and become the ultimate RPS Champion!</i>\n\n"
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
    chat = query.message.chat
    action = query.data
    logger.info(f"Callback received: {action} from user {user.id} in chat {chat.id}")
    
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
            "🏆 <b>Stats & Achievements</b> are tracked globally for all players!\n"
            "📊 Use /stats to see your stats or /leaderboard to view rankings."
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
                # Calculate overall stats
                overall_games = stats['total_games'] + stats['bot_games']
                overall_wins = stats['total_wins'] + stats['bot_wins']
                overall_losses = stats['total_losses'] + stats['bot_losses']
                overall_ties = stats['challenge_ties'] + stats['bot_ties']
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
                moves = {'rock': total_rock, 'paper': total_paper, 'scissor': total_scissor}
                favorite_move = max(moves, key=moves.get) if sum(moves.values()) > 0 else None
                
                stats_text = (
                    f"📊 <b>Stats for {user.first_name}</b> 📊\n\n"
                    f"<b>Level:</b> {stats['level']} ({stats['experience_points']} XP)\n"
                    f"<b>Rank:</b> #{stats['leaderboard_rank']} on the global leaderboard\n\n"
                    
                    f"🎮 <b>Overall Stats:</b>\n"
                    f"Games Played: {overall_games}\n"
                    f"Wins: {overall_wins} ({overall_win_rate}%)\n"
                    f"Losses: {overall_losses}\n"
                    f"Ties: {overall_ties}\n\n"
                    
                    f"🏆 <b>Challenge Mode Stats:</b>\n"
                    f"Games: {challenge_games}\n"
                    f"Wins: {stats['challenge_wins']} ({challenge_win_rate}%)\n"
                    f"Losses: {stats['challenge_losses']}\n"
                    f"Ties: {stats['challenge_ties']}\n\n"
                    
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
                    stats_text += f"Favorite Move: {favorite_move_emoji} {favorite_move.capitalize()}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
            ]
            
            await query.edit_message_caption(
                caption=stats_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error fetching stats for user {user.id}: {e}")
            await query.edit_message_caption(
                caption="⚠️ Error fetching stats. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]),
                parse_mode=ParseMode.HTML
            )
    
    elif action == "quick_game":
        try:
            await start_bot_game(query, context)
        except Exception as e:
            logger.error(f"Error starting bot game for user {user.id}: {e}")
            await query.edit_message_caption(
                caption="⚠️ Error starting quick game. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]),
                parse_mode=ParseMode.HTML
            )
    
    elif action == "leaderboard":
        try:
            category = "wins"
            if chat.type == "private":
                # Show global leaderboard in PM
                leaders = await get_leaderboard(category, 10)
                message, keyboard = await format_leaderboard(leaders, category)
            else:
                # Show group leaderboard in group chat
                group_id = chat.id
                leaders = await get_group_leaderboard(group_id, category, 10)
                message, keyboard = await format_leaderboard(leaders, category, is_group=True, group_id=group_id)
            
            await query.edit_message_caption(
                caption=message,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error fetching leaderboard for user {user.id} in chat {chat.id}: {e}")
            await query.edit_message_caption(
                caption="⚠️ Error fetching leaderboard. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]),
                parse_mode=ParseMode.HTML
            )
    
    elif action == "achievements":
        try:
            achievements = await get_user_achievements(user.id)
            achievements_text = f"🏅 <b>{user.first_name}'s Achievements</b> 🏅\n\n"
            
            if not achievements:
                achievements_text += "No achievements unlocked yet! Keep playing challenge or bot games to earn achievements!"
            else:
                for ach in achievements:
                    achievement_icon = {
                        "perfect_victory": "🌟",
                        "first_win": "🎉",
                        "first_bot_game": "🤖",
                        "first_bot_win": "🎮",
                        "veteran": "🏆",
                        "comeback": "💪",
                        "lucky": "🍀"
                    }.get(ach['achievement_type'], "🎖️")
                    
                    achievements_text += f"{achievement_icon} <b>{ach['achievement_type'].replace('_', ' ').title()}</b>\n"
                    achievements_text += f"<i>{ach['description']}</i>\n"
                    achievements_text += f"Earned on: {ach['achievement_date'].split('T')[0]}\n\n"
            
            await query.edit_message_caption(
                caption=achievements_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Error fetching achievements for user {user.id}: {e}")
            await query.edit_message_caption(
                caption="⚠️ Error fetching achievements. Please try again later.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]),
                parse_mode=ParseMode.HTML
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
            "- Track your global win/loss stats\n"
            "- Earn achievements\n"
            "- Level up as you play\n"
            "- Compete on global or group leaderboards\n"
            "- Play quick games against the bot"
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
                caption="⚠️ Error returning to main menu. Please try again.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]),
                parse_mode=ParseMode.HTML
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
            caption="⚠️ Error starting game. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]),
            parse_mode=ParseMode.HTML
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
            game_type='bot',
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
        stats = await get_user_bot_stats(user.id)
        if stats['total_games'] == 1:
            await add_achievement(user.id, "first_bot_game", "Played your first game against the bot!")
        if result == 'win' and stats['total_wins'] == 1:
            await add_achievement(user.id, "first_bot_win", "Won your first game against the bot!")
    
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
            caption="⚠️ Error displaying game result. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]]),
            parse_mode=ParseMode.HTML
        )
