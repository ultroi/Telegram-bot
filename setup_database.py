import sqlite3

# Connect to the database (this will create the database file if it doesn't exist)
conn = sqlite3.connect('game.db')
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    score INTEGER
    notified BOOLEAN DEFAULT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS games (
    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
    current_round INTEGER
)''')

# Commit changes and close the connection
conn.commit()
conn.close()

print("Database setup completed successfully.")
