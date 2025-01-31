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
            CREATE TABLE IF NOT EXISTS stats (
                user_id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                profile_link TEXT,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                challenge_wins INTEGER DEFAULT 0,
                challenge_losses INTEGER DEFAULT 0
            )
            ''')
            await conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")

async def get_user_stats(user_id):
    """Retrieve a user's statistics from the database."""
    async with get_db_connection() as conn:
        async with conn.execute('SELECT first_name, last_name, profile_link, total_wins, total_losses, challenge_wins, challenge_losses FROM stats WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'first_name': row[0],
                    'last_name': row[1],
                    'profile_link': row[2],
                    'total_wins': row[3],
                    'total_losses': row[4],
                    'challenge_wins': row[5],
                    'challenge_losses': row[6]
                }
            return None

async def update_stats(user_id, first_name, last_name, profile_link, result, is_challenge=False):
    """Update a user's game stats based on the result."""
    async with get_db_connection() as conn:
        async with conn.execute('SELECT total_wins, total_losses, challenge_wins, challenge_losses FROM stats WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                total_wins, total_losses, challenge_wins, challenge_losses = row
                if result == 'win':
                    total_wins += 1
                    if is_challenge:
                        challenge_wins += 1
                elif result == 'loss':
                    total_losses += 1
                    if is_challenge:
                        challenge_losses += 1
                await conn.execute('''UPDATE stats SET 
                    first_name = ?, last_name = ?, profile_link = ?, 
                    total_wins = ?, total_losses = ?, 
                    challenge_wins = ?, challenge_losses = ? 
                    WHERE user_id = ?''', 
                    (first_name, last_name, profile_link, 
                     total_wins, total_losses, 
                     challenge_wins, challenge_losses, 
                     user_id))
            else:
                if result == 'win':
                    await conn.execute('''INSERT INTO stats 
                        (user_id, first_name, last_name, profile_link, 
                        total_wins, total_losses, challenge_wins, challenge_losses) 
                        VALUES (?, ?, ?, ?, 1, 0, ?, ?)''', 
                        (user_id, first_name, last_name, profile_link, 
                         1 if is_challenge else 0, 0))
                elif result == 'loss':
                    await conn.execute('''INSERT INTO stats 
                        (user_id, first_name, last_name, profile_link, 
                        total_wins, total_losses, challenge_wins, challenge_losses) 
                        VALUES (?, ?, ?, ?, 0, 1, 0, ?)''', 
                        (user_id, first_name, last_name, profile_link, 
                         1 if is_challenge else 0))
        await conn.commit()

