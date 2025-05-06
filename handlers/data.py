import logging
import asyncio
import sqlite3
from handlers.connection import get_db_connection, ensure_tables_exist  
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from uuid import uuid4

# Configure logging
logger = logging.getLogger(__name__)

# Admin IDs (replace with your actual admin user IDs)
ADMIN_IDS = [5956598856]  # Update with your admin user IDs

async def is_admin(user_id: int) -> bool:
    """Check if the user is an admin."""
    return user_id in ADMIN_IDS

async def migrate_schema():
    """Migrate the database to the latest schema by recreating tables."""
    async with get_db_connection() as conn:
        try:
            # Drop all existing tables
            await conn.execute('DROP TABLE IF EXISTS users')
            await conn.execute('DROP TABLE IF EXISTS groups')
            await conn.execute('DROP TABLE IF EXISTS stats')
            await conn.execute('DROP TABLE IF EXISTS bot_stats')
            await conn.execute('DROP TABLE IF EXISTS game_history')
            await conn.execute('DROP TABLE IF EXISTS round_details')
            await conn.execute('DROP TABLE IF EXISTS achievements')
            await conn.commit()
            
            # Recreate tables with the latest schema
            await ensure_tables_exist()
            logger.info("Database schema migrated successfully.")
        except sqlite3.Error as e:
            logger.error(f"Error migrating schema: {e}")
            raise

async def list_users() -> str:
    """List all users in the database."""
    async with get_db_connection() as conn:
        async with conn.execute('''
            SELECT user_id, first_name, last_name, username, joined_date, last_active
            FROM users
            ORDER BY user_id
        ''') as cursor:
            users = await cursor.fetchall()
            if not users:
                return "No users found in the database."
            
            result = "📋 <b>User List</b>\n\n"
            for user in users:
                result += (
                    f"ID: {user['user_id']}\n"
                    f"Name: {user['first_name']} {user['last_name'] or ''}\n"
                    f"Username: {user['username'] or 'None'}\n"
                    f"Joined: {user['joined_date']}\n"
                    f"Last Active: {user['last_active']}\n"
                    f"---\n"
                )
            return result

async def list_groups() -> str:
    """List all groups in the database."""
    async with get_db_connection() as conn:
        async with conn.execute('''
            SELECT group_id, title, username, joined_date, last_active, member_count
            FROM groups
            ORDER BY group_id
        ''') as cursor:
            groups = await cursor.fetchall()
            if not groups:
                return "No groups found in the database."
            
            result = "📋 <b>Group List</b>\n\n"
            for group in groups:
                result += (
                    f"ID: {group['group_id']}\n"
                    f"Title: {group['title']}\n"
                    f"Username: {group['username'] or 'None'}\n"
                    f"Joined: {group['joined_date']}\n"
                    f"Last Active: {group['last_active']}\n"
                    f"Members: {group['member_count']}\n"
                    f"---\n"
                )
            return result

async def delete_user_data(user_id: int) -> str:
    """Delete all data related to a specific user."""
    async with get_db_connection() as conn:
        try:
            # Delete from related tables first to avoid foreign key constraints
            await conn.execute('DELETE FROM stats WHERE user_id = ?', (user_id,))
            await conn.execute('DELETE FROM bot_stats WHERE user_id = ?', (user_id,))
            await conn.execute('DELETE FROM achievements WHERE user_id = ?', (user_id,))
            await conn.execute('DELETE FROM round_details WHERE game_id IN (SELECT game_id FROM game_history WHERE player1_id = ? OR player2_id = ?)', (user_id, user_id))
            await conn.execute('DELETE FROM game_history WHERE player1_id = ? OR player2_id = ? OR winner_id = ?', (user_id, user_id, user_id))
            await conn.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            await conn.commit()
            logger.info(f"Deleted data for user {user_id}")
            return f"✅ Successfully deleted all data for user ID {user_id}."
        except sqlite3.Error as e:
            logger.error(f"Error deleting user {user_id}: {e}")
            return f"⚠️ Error deleting user ID {user_id}: {e}"

async def delete_group_data(group_id: int) -> str:
    """Delete all data related to a specific group."""
    async with get_db_connection() as conn:
        try:
            # Delete related game history first
            await conn.execute('DELETE FROM round_details WHERE game_id IN (SELECT game_id FROM game_history WHERE group_id = ?)', (group_id,))
            await conn.execute('DELETE FROM game_history WHERE group_id = ?', (group_id,))
            await conn.execute('DELETE FROM groups WHERE group_id = ?', (group_id,))
            await conn.commit()
            logger.info(f"Deleted data for group {group_id}")
            return f"✅ Successfully deleted all data for group ID {group_id}."
        except sqlite3.Error as e:
            logger.error(f"Error deleting group {group_id}: {e}")
            return f"⚠️ Error deleting group ID {group_id}: {e}"

async def manage_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /manage_data command for database management."""
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            "📊 <b>Data Management Command</b>\n\n"
            "Usage:\n"
            "/manage_data wipe_all - Wipe all database data\n"
            "/manage_data list_users - List all users\n"
            "/manage_data list_groups - List all groups\n"
            "/manage_data delete_user <user_id> - Delete specific user data\n"
            "/manage_data delete_group <group_id> - Delete specific group data\n\n"
            "Please provide a valid action.",
            parse_mode="HTML"
        )
        return

    action = args[0].lower()
    
    if action == "wipe_all":
        # Create confirmation prompt
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm Wipe", callback_data=f"confirm_wipe_all_{user.id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_wipe_all_{user.id}")
            ]
        ]
        await update.message.reply_text(
            "⚠️ <b>WARNING</b>: This will delete ALL data in the database!\n"
            "Are you sure you want to proceed?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    
    elif action == "list_users":
        result = await list_users()
        await update.message.reply_text(result, parse_mode="HTML")
    
    elif action == "list_groups":
        result = await list_groups()
        await update.message.reply_text(result, parse_mode="HTML")
    
    elif action == "delete_user":
        if len(args) < 2:
            await update.message.reply_text("⚠️ Please provide a user ID.\nExample: /manage_data delete_user 123456789")
            return
        try:
            user_id = int(args[1])
            # Create confirmation prompt
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm Delete", callback_data=f"confirm_delete_user_{user_id}_{user.id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_delete_user_{user_id}_{user.id}")
                ]
            ]
            await update.message.reply_text(
                f"⚠️ <b>WARNING</b>: This will delete all data for user ID {user_id}!\n"
                "Are you sure you want to proceed?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        except ValueError:
            await update.message.reply_text("⚠️ Invalid user ID. Please provide a numeric ID.")
    
    elif action == "delete_group":
        if len(args) < 2:
            await update.message.reply_text("⚠️ Please provide a group ID.\nExample: /manage_data delete_group -123456789")
            return
        try:
            group_id = int(args[1])
            # Create confirmation prompt
            keyboard = [
                [
                    InlineKeyboardButton("✅ Confirm Delete", callback_data=f"confirm_delete_group_{group_id}_{user.id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_delete_group_{group_id}_{user.id}")
                ]
            ]
            await update.message.reply_text(
                f"⚠️ <b>WARNING</b>: This will delete all data for group ID {group_id}!\n"
                "Are you sure you want to proceed?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        except ValueError:
            await update.message.reply_text("⚠️ Invalid group ID. Please provide a numeric ID.")
    
    else:
        await update.message.reply_text("⚠️ Invalid action. Use: wipe_all, list_users, list_groups, delete_user, delete_group")

async def manage_data_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks for data management confirmations."""
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if not await is_admin(user.id):
        await query.edit_message_text("🚫 You are not authorized to perform this action.")
        return

    action, *params = query.data.split("_")
    admin_id = int(params[-1])

    if admin_id != user.id:
        await query.edit_message_text("🚫 This action can only be confirmed by the user who initiated it.")
        return

    if action == "confirm_wipe_all":
        try:
            await migrate_schema()
            await query.edit_message_text(
                "✅ <b>Success</b>: All database data has been wiped and the schema has been updated.",
                parse_mode="HTML"
            )
            logger.info(f"User {user.id} wiped all database data.")
        except Exception as e:
            await query.edit_message_text(
                f"⚠️ <b>Error</b>: Failed to wipe database: {e}",
                parse_mode="HTML"
            )
            logger.error(f"Error wiping database by user {user.id}: {e}")

    elif action == "cancel_wipe_all":
        await query.edit_message_text(
            "❌ <b>Cancelled</b>: Database wipe operation cancelled.",
            parse_mode="HTML"
        )
        logger.info(f"User {user.id} cancelled database wipe.")

    elif action == "confirm_delete_user":
        user_id = int(params[0])
        result = await delete_user_data(user_id)
        await query.edit_message_text(result, parse_mode="HTML")

    elif action == "cancel_delete_user":
        user_id = int(params[0])
        await query.edit_message_text(
            f"❌ <b>Cancelled</b>: Deletion of user ID {user_id} cancelled.",
            parse_mode="HTML"
        )
        logger.info(f"User {user.id} cancelled deletion of user {user_id}.")

    elif action == "confirm_delete_group":
        group_id = int(params[0])
        result = await delete_group_data(group_id)
        await query.edit_message_text(result, parse_mode="HTML")

    elif action == "cancel_delete_group":
        group_id = int(params[0])
        await query.edit_message_text(
            f"❌ <b>Cancelled</b>: Deletion of group ID {group_id} cancelled.",
            parse_mode="HTML"
        )
        logger.info(f"User {user.id} cancelled deletion of group {group_id}.")
    elif action == "cancel_delete_group":
      group_id = int(params[0])
      await query.edit_message_text(
        f"❌ <b>Cancelled</b>: Deletion of group ID {group_id} cancelled.",
        parse_mode="HTML"
      )
      logger.info(f"User {user.id} cancelled deletion of group {group_id}.")

