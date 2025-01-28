import sqlite3
from contextlib import asynccontextmanager
import aiosqlite

@asynccontextmanager
async def get_db_connection():
    """Provide an asynchronous SQLite database connection."""
    conn = await aiosqlite.connect('game.db')
    try:
        yield conn
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        await conn.close()

async def ensure_tables_exist():
    """Ensure necessary tables exist in the database."""
    async with get_db_connection() as conn:
        try:
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                multiplayer_moves TEXT,
                caller_name TEXT,
                players TEXT,
                join_timer_active INTEGER
            )
            ''')
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id TEXT PRIMARY KEY,
                wins INTEGER,
                losses INTEGER,
                ties INTEGER
            )
            ''')
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                user_id TEXT PRIMARY KEY,
                last_active TIMESTAMP
            )
            ''')
            await conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")

async def get_game_from_db(game_id):
    """Retrieve a game's data from the database by game_id."""
    async with get_db_connection() as conn:
        async with conn.execute('SELECT multiplayer_moves, caller_name, players, join_timer_active FROM games WHERE game_id = ?', (game_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'multiplayer_moves': eval(row[0]) if row[0] else {},
                    'caller_name': row[1],
                    'players': eval(row[2]) if row[2] else [],
                    'join_timer_active': row[3]
                }
            return None

async def save_game_to_db(game_id, game_data):
    """Save a new game's data to the database."""
    async with get_db_connection() as conn:
        await conn.execute(
            'INSERT INTO games (game_id, multiplayer_moves, caller_name, players, join_timer_active) VALUES (?, ?, ?, ?, ?)',
            (game_id, str(game_data['multiplayer_moves']), game_data['caller_name'], str(game_data['players']), game_data['join_timer_active'])
        )
        await conn.commit()

async def update_game_in_db(game_id, game_data):
    """Update an existing game's data in the database."""
    async with get_db_connection() as conn:
        await conn.execute(
            'UPDATE games SET multiplayer_moves = ?, caller_name = ?, players = ?, join_timer_active = ? WHERE game_id = ?',
            (str(game_data['multiplayer_moves']), game_data['caller_name'], str(game_data['players']), game_data['join_timer_active'], game_id)
        )
        await conn.commit()

async def update_stats(user_id, result):
    """Update a user's game stats based on the result."""
    async with get_db_connection() as conn:
        async with conn.execute('SELECT wins, losses, ties FROM stats WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                wins, losses, ties = row
                if result == 'win':
                    wins += 1
                elif result == 'loss':
                    losses += 1
                elif result == 'tie':
                    ties += 1
                await conn.execute('UPDATE stats SET wins = ?, losses = ?, ties = ? WHERE user_id = ?', (wins, losses, ties, user_id))
            else:
                if result == 'win':
                    await conn.execute('INSERT INTO stats (user_id, wins, losses, ties) VALUES (?, 1, 0, 0)', (user_id,))
                elif result == 'loss':
                    await conn.execute('INSERT INTO stats (user_id, wins, losses, ties) VALUES (?, 0, 1, 0)', (user_id,))
                elif result == 'tie':
                    await conn.execute('INSERT INTO stats (user_id, wins, losses, ties) VALUES (?, 0, 0, 1)', (user_id,))
        await conn.commit()
