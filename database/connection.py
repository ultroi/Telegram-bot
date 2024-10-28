import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('game.db')
    try:
        yield conn
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def ensure_tables_exist():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                multiplayer_moves TEXT,
                caller_name TEXT,
                players TEXT,
                join_timer_active INTEGER
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                user_id TEXT PRIMARY KEY,
                wins INTEGER,
                losses INTEGER,
                ties INTEGER
            )
            ''')
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                user_id TEXT PRIMARY KEY,
                last_active TIMESTAMP
            )
            ''')
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")
        finally:
            cursor.close()

def get_game_from_db(game_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT multiplayer_moves, caller_name, players, join_timer_active FROM games WHERE game_id = ?', (game_id,))
        row = cursor.fetchone()
        if row:
            return {
                'multiplayer_moves': eval(row[0]) if row[0] else {},  # Convert string back to dictionary
                'caller_name': row[1],
                'players': eval(row[2]) if row[2] else [],  # Convert string back to list
                'join_timer_active': row[3]
            }
        return None

def save_game_to_db(game_id, game_data):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO games (game_id, multiplayer_moves, caller_name, players, join_timer_active) VALUES (?, ?, ?, ?, ?)', 
                       (game_id, str(game_data['multiplayer_moves']), game_data['caller_name'], str(game_data['players']), game_data['join_timer_active']))
        conn.commit()

def update_game_in_db(game_id, game_data):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET multiplayer_moves = ?, caller_name = ?, players = ?, join_timer_active = ? WHERE game_id = ?', 
                       (str(game_data['multiplayer_moves']), game_data['caller_name'], str(game_data['players']), game_data['join_timer_active'], game_id))
        conn.commit()

def update_stats(user_id, result):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT wins, losses, ties FROM stats WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            wins, losses, ties = row
            if result == 'win':
                wins += 1
            elif result == 'loss':
                losses += 1
            elif result == 'tie':
                ties += 1
            cursor.execute('UPDATE stats SET wins = ?, losses = ?, ties = ? WHERE user_id = ?', (wins, losses, ties, user_id))
        else:
            if result == 'win':
                cursor.execute('INSERT INTO stats (user_id, wins, losses, ties) VALUES (?, 1, 0, 0)', (user_id,))
            elif result == 'loss':
                cursor.execute('INSERT INTO stats (user_id, wins, losses, ties) VALUES (?, 0, 1, 0)', (user_id,))
            elif result == 'tie':
                cursor.execute('INSERT INTO stats (user_id, wins, losses, ties) VALUES (?, 0, 0, 1)', (user_id,))
        conn.commit()

