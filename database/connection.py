import sqlite3
from contextlib import asynccontextmanager
import aiosqlite
from datetime import datetime, timedelta
import shutil
import os

@asynccontextmanager
async def get_db_connection():
    """Provide an asynchronous SQLite database connection."""
    conn = await aiosqlite.connect('trihand.db')
    try:
        conn.row_factory = aiosqlite.Row
        yield conn
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        await conn.close()

async def is_admin(user_id):
    """Check if a user is an admin."""
    # Replace with your admin IDs
    return user_id in [123456789, 987654321]  # Update with actual admin IDs

async def ensure_tables_exist():
    """Ensure all necessary tables and indexes exist in the database."""
    async with get_db_connection() as conn:
        try:
            # Users table
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT,
                username TEXT,
                joined_date TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP
            )
            ''')

            # Groups table
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                username TEXT,
                joined_date TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active TEXT DEFAULT CURRENT_TIMESTAMP,
                member_count INTEGER DEFAULT 0
            )
            ''')

            # Challenge stats table
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id INTEGER PRIMARY KEY,
                total_games INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                challenge_ties INTEGER DEFAULT 0,
                challenge_games INTEGER DEFAULT 0,
                challenge_wins INTEGER DEFAULT 0,
                challenge_losses INTEGER DEFAULT 0,
                rock_played INTEGER DEFAULT 0,
                paper_played INTEGER DEFAULT 0,
                scissor_played INTEGER DEFAULT 0,
                experience_points INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            ''')

            # Bot stats table
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS bot_stats (
                user_id INTEGER PRIMARY KEY,
                total_games INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                total_ties INTEGER DEFAULT 0,
                rock_played INTEGER DEFAULT 0,
                paper_played INTEGER DEFAULT 0,
                scissor_played INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            ''')

            # Game history table
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS game_history (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player1_id INTEGER NOT NULL,
                player2_id INTEGER,
                winner_id INTEGER,
                game_type TEXT CHECK(game_type IN ('challenge', 'bot')) NOT NULL,
                rounds INTEGER DEFAULT 1,
                date_played TEXT DEFAULT CURRENT_TIMESTAMP,
                group_id INTEGER,
                FOREIGN KEY (player1_id) REFERENCES users(user_id),
                FOREIGN KEY (player2_id) REFERENCES users(user_id),
                FOREIGN KEY (winner_id) REFERENCES users(user_id),
                FOREIGN KEY (group_id) REFERENCES groups(group_id)
            )
            ''')

            # Round details table
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS round_details (
                round_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                round_number INTEGER NOT NULL,
                player1_move TEXT CHECK(player1_move IN ('rock', 'paper', 'scissor')) NOT NULL,
                player2_move TEXT CHECK(player2_move IN ('rock', 'paper', 'scissor')) NOT NULL,
                winner_id INTEGER,
                FOREIGN KEY (game_id) REFERENCES game_history(game_id),
                FOREIGN KEY (winner_id) REFERENCES users(user_id)
            )
            ''')

            # Achievements table
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_type TEXT CHECK(achievement_type IN (
                    'first_win', 'first_bot_game', 'first_bot_win', 'perfect_victory',
                    'veteran', 'comeback', 'lucky', 'streak_winner', 'move_master'
                )) NOT NULL,
                achievement_date TEXT DEFAULT CURRENT_TIMESTAMP,
                description TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            ''')

            # User progress table for achievement tracking
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER PRIMARY KEY,
                win_streak INTEGER DEFAULT 0,
                last_move TEXT CHECK(last_move IN ('rock', 'paper', 'scissor', '')) DEFAULT '',
                move_streak INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            ''')

            # Create indexes for performance
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_game_history_group ON game_history(group_id, game_type)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_game_history_players ON game_history(player1_id, player2_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_game_history_date ON game_history(date_played)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_stats_ranking ON stats(total_wins, level, experience_points)')

            await conn.commit()
            print("All tables and indexes created successfully!")
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")

async def update_user_activity(user_id, first_name, last_name=None, username=None):
    """Update user information and last active timestamp."""
    current_time = datetime.now().isoformat()
    
    async with get_db_connection() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, first_name, last_name, username, last_active)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                username = excluded.username,
                last_active = excluded.last_active
        ''', (user_id, first_name, last_name or "", username or "", current_time))
        
        # Initialize stats for challenge mode
        await conn.execute('''
            INSERT INTO stats (user_id)
            VALUES (?)
            ON CONFLICT(user_id) DO NOTHING
        ''', (user_id,))
        
        # Initialize stats for bot games
        await conn.execute('''
            INSERT INTO bot_stats (user_id)
            VALUES (?)
            ON CONFLICT(user_id) DO NOTHING
        ''', (user_id,))
        
        # Initialize user progress for achievements
        await conn.execute('''
            INSERT INTO user_progress (user_id)
            VALUES (?)
            ON CONFLICT(user_id) DO NOTHING
        ''', (user_id,))
        
        await conn.commit()

async def update_group_activity(group_id, title, username=None, member_count=None):
    """Update group information and last active timestamp."""
    current_time = datetime.now().isoformat()
    
    async with get_db_connection() as conn:
        await conn.execute('''
            INSERT INTO groups (group_id, title, username, last_active, member_count)
            VALUES (?, ?, ?, ?, COALESCE(?, 0))
            ON CONFLICT(group_id) DO UPDATE SET
                title = excluded.title,
                username = excluded.username,
                last_active = excluded.last_active,
                member_count = COALESCE(excluded.member_count, member_count)
        ''', (group_id, title, username or "", current_time, member_count))
        
        await conn.commit()

async def update_stats(user_id, game_type, result, move=None):
    """Update user challenge mode statistics after a game."""
    if game_type != 'challenge':
        return False, 1
    
    async with get_db_connection() as conn:
        # Fetch current stats
        async with conn.execute('SELECT * FROM stats WHERE user_id = ?', (user_id,)) as cursor:
            stats = await cursor.fetchone()
            
            if not stats:
                await conn.execute('''
                    INSERT INTO stats (user_id) VALUES (?)
                ''', (user_id,))
                stats = {
                    'total_games': 0, 'total_wins': 0, 'total_losses': 0, 'challenge_ties': 0,
                    'challenge_games': 0, 'challenge_wins': 0, 'challenge_losses': 0,
                    'rock_played': 0, 'paper_played': 0, 'scissor_played': 0,
                    'experience_points': 0, 'level': 1
                }
        
        # Update move counts
        if move:
            if move == 'rock':
                rock_played = stats['rock_played'] + 1
                await conn.execute('UPDATE stats SET rock_played = ? WHERE user_id = ?', 
                                (rock_played, user_id))
            elif move == 'paper':
                paper_played = stats['paper_played'] + 1
                await conn.execute('UPDATE stats SET paper_played = ? WHERE user_id = ?', 
                                (paper_played, user_id))
            elif move == 'scissor':
                scissor_played = stats['scissor_played'] + 1
                await conn.execute('UPDATE stats SET scissor_played = ? WHERE user_id = ?', 
                                (scissor_played, user_id))
        
        # Update game stats
        total_games = stats['total_games'] + 1
        challenge_games = stats['challenge_games'] + 1
        experience_points = stats['experience_points']
        
        # Update result stats
        xp_gain = 0
        if result == 'win':
            total_wins = stats['total_wins'] + 1
            challenge_wins = stats['challenge_wins'] + 1
            xp_gain = 15
            await conn.execute('UPDATE stats SET total_wins = ?, challenge_wins = ? WHERE user_id = ?', 
                            (total_wins, challenge_wins, user_id))
        elif result == 'loss':
            total_losses = stats['total_losses'] + 1
            challenge_losses = stats['challenge_losses'] + 1
            xp_gain = 3
            await conn.execute('UPDATE stats SET total_losses = ?, challenge_losses = ? WHERE user_id = ?', 
                            (total_losses, challenge_losses, user_id))
        elif result == 'tie':
            challenge_ties = stats['challenge_ties'] + 1
            xp_gain = 5
            await conn.execute('UPDATE stats SET challenge_ties = ? WHERE user_id = ?', 
                            (challenge_ties, user_id))
        
        # Update total games, challenge games, and XP
        experience_points += xp_gain
        level = calculate_level(experience_points)
        
        await conn.execute('''
            UPDATE stats SET 
                total_games = ?,
                challenge_games = ?,
                experience_points = ?,
                level = ?
            WHERE user_id = ?
        ''', (total_games, challenge_games, experience_points, level, user_id))
        
        await conn.commit()
        
        if level > stats['level']:
            return True, level
        return False, level

async def update_bot_stats(user_id, result, move=None):
    """Update user bot game statistics after a game."""
    async with get_db_connection() as conn:
        async with conn.execute('SELECT * FROM bot_stats WHERE user_id = ?', (user_id,)) as cursor:
            stats = await cursor.fetchone()
            
            if not stats:
                await conn.execute('''
                    INSERT INTO bot_stats (user_id) VALUES (?)
                ''', (user_id,))
                stats = {
                    'total_games': 0,
                    'total_wins': 0,
                    'total_losses': 0,
                    'total_ties': 0,
                    'rock_played': 0,
                    'paper_played': 0,
                    'scissor_played': 0
                }
        
        if move:
            if move == 'rock':
                rock_played = stats['rock_played'] + 1
                await conn.execute('UPDATE bot_stats SET rock_played = ? WHERE user_id = ?', 
                                (rock_played, user_id))
            elif move == 'paper':
                paper_played = stats['paper_played'] + 1
                await conn.execute('UPDATE bot_stats SET paper_played = ? WHERE user_id = ?', 
                                (paper_played, user_id))
            elif move == 'scissor':
                scissor_played = stats['scissor_played'] + 1
                await conn.execute('UPDATE bot_stats SET scissor_played = ? WHERE user_id = ?', 
                                (scissor_played, user_id))
        
        total_games = stats['total_games'] + 1
        
        if result == 'win':
            total_wins = stats['total_wins'] + 1
            await conn.execute('UPDATE bot_stats SET total_wins = ? WHERE user_id = ?', 
                            (total_wins, user_id))
        elif result == 'loss':
            total_losses = stats['total_losses'] + 1
            await conn.execute('UPDATE bot_stats SET total_losses = ? WHERE user_id = ?', 
                            (total_losses, user_id))
        elif result == 'tie':
            total_ties = stats['total_ties'] + 1
            await conn.execute('UPDATE bot_stats SET total_ties = ? WHERE user_id = ?', 
                            (total_ties, user_id))
        
        await conn.execute('UPDATE bot_stats SET total_games = ? WHERE user_id = ?', 
                         (total_games, user_id))
        
        await conn.commit()

async def update_user_progress(user_id, result, move=None):
    """Update user progress for achievement tracking."""
    async with get_db_connection() as conn:
        # Fetch current progress
        async with conn.execute('SELECT * FROM user_progress WHERE user_id = ?', (user_id,)) as cursor:
            progress = await cursor.fetchone()
            
            if not progress:
                await conn.execute('''
                    INSERT INTO user_progress (user_id) VALUES (?)
                ''', (user_id,))
                progress = {'win_streak': 0, 'last_move': '', 'move_streak': 0}
        
        # Update win streak
        win_streak = progress['win_streak']
        if result == 'win':
            win_streak += 1
        else:
            win_streak = 0
        
        # Update move streak
        last_move = progress['last_move']
        move_streak = progress['move_streak']
        
        if move and move in ('rock', 'paper', 'scissor'):
            if last_move == move:
                move_streak += 1
            else:
                move_streak = 1
            last_move = move
        else:
            move_streak = 0
            last_move = ''
        
        # Update progress
        await conn.execute('''
            UPDATE user_progress SET
                win_streak = ?,
                last_move = ?,
                move_streak = ?
            WHERE user_id = ?
        ''', (win_streak, last_move, move_streak, user_id))
        
        await conn.commit()
        
        return {'win_streak': win_streak, 'move_streak': move_streak}

def calculate_level(xp):
    """Calculate user level based on experience points."""
    if xp < 100:
        return 1
    elif xp < 250:
        return 2
    elif xp < 450:
        return 3
    elif xp < 700:
        return 4
    elif xp < 1000:
        return 5
    else:
        return 5 + (xp - 1000) // 500

async def record_round(game_id, round_number, player1_move, player2_move, winner_id=None):
    """Record details of an individual round."""
    async with get_db_connection() as conn:
        await conn.execute('''
            INSERT INTO round_details 
            (game_id, round_number, player1_move, player2_move, winner_id) 
            VALUES (?, ?, ?, ?, ?)
        ''', (game_id, round_number, player1_move, player2_move, winner_id))
        await conn.commit()

async def record_game(player1_id, player2_id, winner_id, game_type, rounds, group_id=None):
    """Record a completed game in the history."""
    async with get_db_connection() as conn:
        cursor = await conn.execute('''
            INSERT INTO game_history 
            (player1_id, player2_id, winner_id, game_type, rounds, group_id) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (player1_id, player2_id, winner_id, game_type, rounds, group_id))
        game_id = cursor.lastrowid
        await conn.commit()
        return game_id

async def get_leaderboard(category='wins', limit=10):
    """Get the global leaderboard for challenge mode statistics."""
    query_map = {
        'wins': '''
            SELECT u.user_id, u.first_name, u.last_name, s.total_wins, s.level, s.experience_points
            FROM users u
            JOIN stats s ON u.user_id = s.user_id
            ORDER BY s.total_wins DESC
            LIMIT ?
        ''',
        'challenge_wins': '''
            SELECT u.user_id, u.first_name, u.last_name, s.challenge_wins, s.level, s.experience_points
            FROM users u
            JOIN stats s ON u.user_id = s.user_id
            ORDER BY s.challenge_wins DESC
            LIMIT ?
        ''',
        'level': '''
            SELECT u.user_id, u.first_name, u.last_name, s.level, s.experience_points
            FROM users u
            JOIN stats s ON u.user_id = s.user_id
            ORDER BY s.level DESC, s.experience_points DESC
            LIMIT ?
        ''',
        'games': '''
            SELECT u.user_id, u.first_name, u.last_name, s.total_games, s.level
            FROM users u
            JOIN stats s ON u.user_id = s.user_id
            ORDER BY s.total_games DESC
            LIMIT ?
        '''
    }
    
    query = query_map.get(category, query_map['wins'])
    
    async with get_db_connection() as conn:
        async with conn.execute(query, (limit,)) as cursor:
            results = await cursor.fetchall()
            return [dict(result) for result in results]

async def get_group_leaderboard(group_id: int, category: str, limit: int = 10) -> list:
    """Get the leaderboard for users who played in a specific group."""
    query_map = {
        'wins': '''
            SELECT u.user_id, u.first_name, u.last_name, s.total_wins, s.level, s.experience_points
            FROM users u
            JOIN stats s ON u.user_id = s.user_id
            WHERE u.user_id IN (
                SELECT DISTINCT player1_id FROM game_history WHERE group_id = ? AND game_type = 'challenge'
                UNION
                SELECT DISTINCT player2_id FROM game_history WHERE group_id = ? AND game_type = 'challenge' AND player2_id IS NOT NULL
            )
            ORDER BY s.total_wins DESC
            LIMIT ?
        ''',
        'challenge_wins': '''
            SELECT u.user_id, u.first_name, u.last_name, s.challenge_wins, s.level, s.experience_points
            FROM users u
            JOIN stats s ON u.user_id = s.user_id
            WHERE u.user_id IN (
                SELECT DISTINCT player1_id FROM game_history WHERE group_id = ? AND game_type = 'challenge'
                UNION
                SELECT DISTINCT player2_id FROM game_history WHERE group_id = ? AND game_type = 'challenge' AND player2_id IS NOT NULL
            )
            ORDER BY s.challenge_wins DESC
            LIMIT ?
        ''',
        'level': '''
            SELECT u.user_id, u.first_name, u.last_name, s.level, s.experience_points
            FROM users u
            JOIN stats s ON u.user_id = s.user_id
            WHERE u.user_id IN (
                SELECT DISTINCT player1_id FROM game_history WHERE group_id = ? AND game_type = 'challenge'
                UNION
                SELECT DISTINCT player2_id FROM game_history WHERE group_id = ? AND game_type = 'challenge' AND player2_id IS NOT NULL
            )
            ORDER BY s.level DESC, s.experience_points DESC
            LIMIT ?
        ''',
        'games': '''
            SELECT u.user_id, u.first_name, u.last_name, s.total_games, s.level
            FROM users u
            JOIN stats s ON u.user_id = s.user_id
            WHERE u.user_id IN (
                SELECT DISTINCT player1_id FROM game_history WHERE group_id = ? AND game_type = 'challenge'
                UNION
                SELECT DISTINCT player2_id FROM game_history WHERE group_id = ? AND game_type = 'challenge' AND player2_id IS NOT NULL
            )
            ORDER BY s.total_games DESC
            LIMIT ?
        '''
    }
    
    query = query_map.get(category, query_map['wins'])
    
    async with get_db_connection() as conn:
        async with conn.execute(query, (group_id, group_id, limit)) as cursor:
            results = await cursor.fetchall()
            return [dict(result) for result in results]

async def get_user_stats(user_id):
    """Get comprehensive stats for a user, including challenge and bot games."""
    async with get_db_connection() as conn:
        # Fetch challenge stats
        async with conn.execute('''
            SELECT u.first_name, u.last_name, u.username, u.joined_date,
                   s.total_games, s.total_wins, s.total_losses, s.challenge_ties,
                   s.challenge_games, s.challenge_wins, s.challenge_losses,
                   s.rock_played, s.paper_played, s.scissor_played,
                   s.experience_points, s.level
            FROM users u
            LEFT JOIN stats s ON u.user_id = s.user_id
            WHERE u.user_id = ?
        ''', (user_id,)) as cursor:
            user_stats = await cursor.fetchone()
            
            if not user_stats:
                return None
                
        # Fetch bot stats
        async with conn.execute('''
            SELECT total_games AS bot_games, total_wins AS bot_wins, total_losses AS bot_losses,
                   total_ties AS bot_ties, rock_played AS bot_rock_played,
                   paper_played AS bot_paper_played, scissor_played AS bot_scissor_played
            FROM bot_stats
            WHERE user_id = ?
        ''', (user_id,)) as cursor:
            bot_stats = await cursor.fetchone()
            
            if not bot_stats:
                bot_stats = {
                    'bot_games': 0,
                    'bot_wins': 0,
                    'bot_losses': 0,
                    'bot_ties': 0,
                    'bot_rock_played': 0,
                    'bot_paper_played': 0,
                    'bot_scissor_played': 0
                }
            else:
                bot_stats = dict(bot_stats)
        
        # Calculate challenge mode win rate
        total_games = user_stats['total_games']
        win_rate = round((user_stats['total_wins'] / total_games) * 100, 1) if total_games > 0 else 0
        
        # Calculate bot mode win rate
        bot_games = bot_stats['bot_games']
        bot_win_rate = round((bot_stats['bot_wins'] / bot_games) * 100, 1) if bot_games > 0 else 0
        
        # Get favorite move for challenge mode
        moves = {
            'rock': user_stats['rock_played'],
            'paper': user_stats['paper_played'],
            'scissor': user_stats['scissor_played']
        }
        favorite_move = max(moves, key=moves.get) if sum(moves.values()) > 0 else None
        
        # Get favorite move for bot mode
        bot_moves = {
            'rock': bot_stats['bot_rock_played'],
            'paper': bot_stats['bot_paper_played'],
            'scissor': bot_stats['bot_scissor_played']
        }
        bot_favorite_move = max(bot_moves, key=bot_moves.get) if sum(bot_moves.values()) > 0 else None
        
        # Get position on challenge mode leaderboard
        async with conn.execute('''
            SELECT COUNT(*) + 1 as rank
            FROM stats
            WHERE total_wins > (SELECT total_wins FROM stats WHERE user_id = ?)
        ''', (user_id,)) as rank_cursor:
            rank = await rank_cursor.fetchone()
                
        result = dict(user_stats)
        result.update({
            'win_rate': win_rate,
            'favorite_move': favorite_move,
            'leaderboard_rank': rank['rank'],
            'bot_games': bot_stats['bot_games'],
            'bot_wins': bot_stats['bot_wins'],
            'bot_losses': bot_stats['bot_losses'],
            'bot_ties': bot_stats['bot_ties'],
            'bot_win_rate': bot_win_rate,
            'bot_favorite_move': bot_favorite_move,
            'bot_rock_played': bot_stats['bot_rock_played'],
            'bot_paper_played': bot_stats['bot_paper_played'],
            'bot_scissor_played': bot_stats['bot_scissor_played']
        })
        
        return result

async def get_system_stats():
    """Get overall system statistics."""
    async with get_db_connection() as conn:
        async with conn.execute('SELECT COUNT(*) as count FROM users') as cursor:
            users_count = (await cursor.fetchone())['count']
            
        async with conn.execute('SELECT COUNT(*) as count FROM groups') as cursor:
            groups_count = (await cursor.fetchone())['count']
            
        async with conn.execute('SELECT COUNT(*) as count FROM game_history') as cursor:
            games_count = departe.cursor.fetchone()['count']
            
        seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
        async with conn.execute('SELECT COUNT(*) as count FROM users WHERE last_active > ?', 
                              (seven_days_ago,)) as cursor:
            active_users = (await cursor.fetchone())['count']
            
        return {
            'total_users': users_count,
            'total_groups': groups_count,
            'total_games': games_count,
            'active_users': active_users
        }

async def get_user_bot_stats(user_id):
    """Get bot game statistics for a user."""
    async with get_db_connection() as conn:
        async with conn.execute('''
            SELECT total_games, total_wins, total_losses, total_ties,
                   rock_played, paper_played, scissor_played
            FROM bot_stats
            WHERE user_id = ?
        ''', (user_id,)) as cursor:
            bot_stats = await cursor.fetchone()
            
            if not bot_stats:
                return {
                    'total_games': 0,
                    'total_wins': 0,
                    'total_losses': 0,
                    'total_ties': 0,
                    'rock_played': 0,
                    'paper_played': 0,
                    'scissor_played': 0
                }
            
            return dict(bot_stats)

async def get_broadcast_users():
    """Get list of all user IDs for broadcasting."""
    async with get_db_connection() as conn:
        async with conn.execute('SELECT user_id FROM users') as cursor:
            users = await cursor.fetchall()
            return [user['user_id'] for user in users]

async def add_achievement(user_id, achievement_type, description):
    """Add a new achievement for a user."""
    async with get_db_connection() as conn:
        await conn.execute('''
            INSERT INTO achievements (user_id, achievement_type, description)
            VALUES (?, ?, ?)
        ''', (user_id, achievement_type, description))
        await conn.commit()

async def get_user_achievements(user_id):
    """Get all achievements for a user."""
    async with get_db_connection() as conn:
        async with conn.execute('''
            SELECT achievement_type, description, achievement_date
            FROM achievements
            WHERE user_id = ?
            ORDER BY achievement_date DESC
        ''', (user_id,)) as cursor:
            achievements = await cursor.fetchall()
            return [dict(achievement) for achievement in achievements]

async def update_game_winner(game_id, winner_id):
    """Update the game record with the winner."""
    async with get_db_connection() as conn:
        await conn.execute('''
            UPDATE game_history SET winner_id = ? WHERE game_id = ?
        ''', (winner_id, game_id))
        await conn.commit()

async def get_last_moves(game_id):
    """Retrieve the last moves for both players from round_details."""
    async with get_db_connection() as conn:
        async with conn.execute('''
            SELECT player1_move, player2_move
            FROM round_details
            WHERE game_id = ?
            ORDER BY round_number DESC
            LIMIT 1
        ''', (game_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row['player1_move'], row['player2_move']
            return None, None

async def list_users(raw=False):
    """List all users in the database."""
    async with get_db_connection() as conn:
        async with conn.execute('SELECT user_id, first_name, last_name, username FROM users') as cursor:
            users = await cursor.fetchall()
            if raw:
                return [dict(user) for user in users]
            return "\n".join([f"ID: {u['user_id']}, Name: {u['first_name']} {u['last_name'] or ''}" for u in users]) or "No users found."

async def list_groups(raw=False):
    """List all groups in the database."""
    async with get_db_connection() as conn:
        async with conn.execute('SELECT group_id, title, username FROM groups') as cursor:
            groups = await cursor.fetchall()
            if raw:
                return [dict(group) for group in groups]
            return "\n".join([f"ID: {g['group_id']}, Title: {g['title']}" for g in groups]) or "No groups found."

async def delete_user_data(user_id):
    """Delete all data for a specific user."""
    async with get_db_connection() as conn:
        await conn.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        await conn.execute('DELETE FROM stats WHERE user_id = ?', (user_id,))
        await conn.execute('DELETE FROM bot_stats WHERE user_id = ?', (user_id,))
        await conn.execute('DELETE FROM achievements WHERE user_id = ?', (user_id,))
        await conn.execute('DELETE FROM user_progress WHERE user_id = ?', (user_id,))
        await conn.execute('DELETE FROM game_history WHERE player1_id = ? OR player2_id = ?', (user_id, user_id))
        await conn.commit()
    return f"✅ User ID {user_id} deleted successfully."

async def delete_group_data(group_id):
    """Delete all data for a specific group."""
    async with get_db_connection() as conn:
        await conn.execute('DELETE FROM groups WHERE group_id = ?', (group_id,))
        await conn.execute('DELETE FROM game_history WHERE group_id = ?', (group_id,))
        await conn.commit()
    return f"✅ Group ID {group_id} deleted successfully."

async def backup_database():
    """Backup the database before migration."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"trihand_backup_{timestamp}.db"
    shutil.copy('trihand.db', backup_file)
    print(f"Database backed up to {backup_file}")

async def migrate_schema():
    """Wipe and recreate all database tables with backup."""
    await backup_database()
    async with get_db_connection() as conn:
        try:
            await conn.execute('DROP TABLE IF EXISTS users')
            await conn.execute('DROP TABLE IF EXISTS groups')
            await conn.execute('DROP TABLE IF EXISTS stats')
            await conn.execute('DROP TABLE IF EXISTS bot_stats')
            await conn.execute('DROP TABLE IF EXISTS game_history')
            await conn.execute('DROP TABLE IF EXISTS round_details')
            await conn.execute('DROP TABLE IF EXISTS achievements')
            await conn.execute('DROP TABLE IF EXISTS user_progress')
            await conn.commit()
            
            await ensure_tables_exist()
            print("Database schema migrated successfully!")
        except sqlite3.Error as e:
            print(f"Error during schema migration: {e}")
            raise

async def migrate_stats():
    """Migrate stats table to new schema without data loss."""
    async with get_db_connection() as conn:
        try:
            await backup_database()
            
            # Check if achievements table needs schema update
            async with conn.execute("PRAGMA table_info(achievements)") as cursor:
                columns = [row['name'] for row in await cursor.fetchall()]
                if 'achievement_type' in columns:
                    async with conn.execute("SELECT achievement_type FROM achievements LIMIT 1") as cursor:
                        row = await cursor.fetchone()
                        if row and 'streak_winner' not in row['achievement_type']:
                            # Create new achievements table
                            await conn.execute('''
                                CREATE TABLE achievements_new (
                                    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    user_id INTEGER NOT NULL,
                                    achievement_type TEXT CHECK(achievement_type IN (
                                        'first_win', 'first_bot_game', 'first_bot_win', 'perfect_victory',
                                        'veteran', 'comeback', 'lucky', 'streak_winner', 'move_master'
                                    )) NOT NULL,
                                    achievement_date TEXT DEFAULT CURRENT_TIMESTAMP,
                                    description TEXT NOT NULL,
                                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                                )
                            ''')
                            await conn.execute('''
                                INSERT INTO achievements_new (achievement_id, user_id, achievement_type, achievement_date, description)
                                SELECT achievement_id, user_id, achievement_type, achievement_date, description
                                FROM achievements
                            ''')
                            await conn.execute('DROP TABLE achievements')
                            await conn.execute('ALTER TABLE achievements_new RENAME TO achievements')
                            print("Updated achievements table schema")
            
            # Create user_progress if not exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_progress (
                    user_id INTEGER PRIMARY KEY,
                    win_streak INTEGER DEFAULT 0,
                    last_move TEXT CHECK(last_move IN ('rock', 'paper', 'scissor', '')) DEFAULT '',
                    move_streak INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Initialize user_progress for existing users
            await conn.execute('''
                INSERT OR IGNORE INTO user_progress (user_id)
                SELECT user_id FROM users
            ''')
            
            # Check if stats table needs total_ties migration
            async with conn.execute("PRAGMA table_info(stats)") as cursor:
                columns = [row['name'] for row in await cursor.fetchall()]
                if 'total_ties' in columns:
                    await conn.execute('ALTER TABLE stats RENAME COLUMN total_ties TO challenge_ties')
                    print("Renamed stats.total_ties to stats.challenge_ties")
            
            # Ensure bot_stats table exists
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bot_stats (
                    user_id INTEGER PRIMARY KEY,
                    total_games INTEGER DEFAULT 0,
                    total_wins INTEGER DEFAULT 0,
                    total_losses INTEGER DEFAULT 0,
                    total_ties INTEGER DEFAULT 0,
                    rock_played INTEGER DEFAULT 0,
                    paper_played INTEGER DEFAULT 0,
                    scissor_played INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Migrate bot game stats if needed
            await conn.execute('''
                INSERT OR IGNORE INTO bot_stats (user_id, total_games, total_wins, total_losses, total_ties,
                                              rock_played, paper_played, scissor_played)
                SELECT user_id, total_games, total_wins, total_losses, challenge_ties,
                       rock_played, paper_played, scissor_played
                FROM stats
                WHERE user_id IN (
                    SELECT player1_id FROM game_history WHERE game_type = 'regular'
                )
            ''')
            
            # Update game_history
            await conn.execute('UPDATE game_history SET game_type = "bot" WHERE game_type = "regular"')
            
            await conn.commit()
            print("Stats migration completed successfully!")
        except sqlite3.Error as e:
            print(f"Error during stats migration: {e}")
            raise
