from telegram import Update
from telegram.ext import ChatMemberHandler, ContextTypes
import logging
from database.connection import update_group_activity, remove_group

logger = logging.getLogger(__name__)

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle updates to the bot's chat member status (added/removed from groups)."""
    my_chat_member = update.my_chat_member
    chat = my_chat_member.chat
    new_status = my_chat_member.new_chat_member.status
    old_status = my_chat_member.old_chat_member.status

    logger.info(f"Chat member update: chat_id={chat.id}, new_status={new_status}, old_status={old_status}")

    if chat.type in ("group", "supergroup"):
        if new_status in ("member", "administrator") and old_status in ("left", "kicked"):
            # Bot was added to the group
            try:
                member_count = await context.bot.get_chat_member_count(chat.id)
                await update_group_activity(
                    group_id=chat.id,
                    title=chat.title or "Untitled Group",
                    username=chat.username,
                    member_count=member_count
                )
                logger.info(f"Bot added to group ID {chat.id}: {chat.title}")
            except Exception as e:
                logger.error(f"Error updating group {chat.id}: {e}")
        elif new_status in ("left", "kicked") and old_status in ("member", "administrator"):
            # Bot was removed from the group
            try:
                await remove_group(chat.id)
                logger.info(f"Bot removed from group ID {chat.id}")
            except Exception as e:
                logger.error(f"Error removing group {chat.id}: {e}")
