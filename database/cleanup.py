import asyncio
from datetime import datetime, timedelta
from .connection import get_db_connection

async def cleanup_inactive_users():
    while True:
        current_time = datetime.now()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, last_active FROM user_activity')
            users = cursor.fetchall()
            for user_id, last_active in users:
                last_active_time = datetime.fromisoformat(last_active)
                if current_time - last_active_time > timedelta(days=30):
                    cursor.execute('DELETE FROM user_activity WHERE user_id = ?', (user_id,))
                    conn.commit()
        await asyncio.sleep(86400)  # Check once a day