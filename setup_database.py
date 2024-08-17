import sqlite3

def setup_database():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()

    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        score INTEGER,
        notified BOOLEAN DEFAULT FALSE
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS games (
        game_id INTEGER PRIMARY KEY,
        current_round INTEGER
    )''')

    # Add 'notified' column if it doesn't exist
    try:
        c.execute("ALTER TABLE players ADD COLUMN notified BOOLEAN DEFAULT FALSE")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_database()
