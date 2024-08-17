import sqlite3

def setup_database():
    """
    Sets up the SQLite database with the required tables and columns.
    If the tables already exist, it will not recreate them.
    """
    conn = sqlite3.connect('game.db')
    c = conn.cursor()

    # Create 'players' table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS players (
        user_id INTEGER PRIMARY KEY,
        score INTEGER,
        notified BOOLEAN DEFAULT FALSE
    )''')

    # Create 'games' table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS games (
        game_id INTEGER PRIMARY KEY,
        current_round INTEGER
    )''')

    # Add 'notified' column to 'players' table if it doesn't exist
    try:
        c.execute("ALTER TABLE players ADD COLUMN notified BOOLEAN DEFAULT FALSE")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Commit changes and close the connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    setup_database()
