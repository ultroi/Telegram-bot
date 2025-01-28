import asyncio
from datetime import datetime, timedelta
from .connection import get_db_connection

async def cleanup_inactive_users():
    """Periodically clean up inactive users from the database."""
    while True:
        current_time = datetime.now()

        # Open a database connection
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Fetch all user activity
            cursor.execute('SELECT user_id, last_active FROM user_activity')
            users = cursor.fetchall()

            # Iterate through users to find and remove inactive ones
            for user_id, last_active in users:
                last_active_time = datetime.fromisoformat(last_active)
                if current_time - last_active_time > timedelta(days=30):
                    cursor.execute('DELETE FROM user_activity WHERE user_id = ?', (user_id,))
                    conn.commit()

        # Wait for a day before running the next cleanup
        await asyncio.sleep(86400)
