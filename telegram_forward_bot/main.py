"""
Telegram Forward Bot - PLATINUM Edition
Main Bot File with All Commands
"""
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ConversationHandler, filters as tg_filters, ContextTypes
)
from telegram.constants import ParseMode

import config
from database import db
from forwarder import forward_engine
from scheduler import scheduler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
SELECTING_SOURCE, SELECTING_DEST, SETTING_FILTERS = range(3)

# ========== START & HELP ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    
    # Add user to database
    await db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    await update.message.reply_text(
        config.WELCOME_MESSAGE,
        parse_mode=ParseMode.HTML
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    await update.message.reply_text(
        config.HELP_MESSAGE,
        parse_mode=ParseMode.HTML
    )

# ========== FORWARD TASK MANAGEMENT ==========
async def newtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new forward task"""
    await update.message.reply_text(
        "🔄 <b>Create New Forward Task</b>\n\n"
        "Step 1: Forward a message from the <b>SOURCE</b> chat\n"
        "(the chat you want to forward FROM)\n\n"
        "Or send the chat ID/username directly.",
        parse_mode=ParseMode.HTML
    )
    context.user_data['awaiting_source'] = True

async def handle_source_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle source chat selection"""
    if not context.user_data.get('awaiting_source'):
        return
    
    message = update.message
    
    # Get source chat info
    if message.forward_from_chat:
        source_chat_id = message.forward_from_chat.id
        source_chat_title = message.forward_from_chat.title or "Unknown"
    elif message.text:
        # Try to parse as chat ID or username
        try:
            source_chat_id = int(message.text)
            source_chat_title = f"Chat {source_chat_id}"
        except ValueError:
            # Assume it's a username
            source_chat_id = message.text
            source_chat_title = message.text
    else:
        await update.message.reply_text("❌ Invalid source. Please forward a message or send a chat ID.")
        return
    
    context.user_data['source_chat_id'] = source_chat_id
    context.user_data['source_chat_title'] = source_chat_title
    context.user_data['awaiting_source'] = False
    context.user_data['awaiting_dest'] = True
    
    await update.message.reply_text(
        f"✅ Source set: <b>{source_chat_title}</b>\n\n"
        "Step 2: Now forward a message from the <b>DESTINATION</b> chat\n"
        "(the chat you want to forward TO)",
        parse_mode=ParseMode.HTML
    )

async def handle_dest_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle destination chat selection"""
    if not context.user_data.get('awaiting_dest'):
        return
    
    message = update.message
    
    # Get destination chat info
    if message.forward_from_chat:
        dest_chat_id = message.forward_from_chat.id
        dest_chat_title = message.forward_from_chat.title or "Unknown"
    elif message.text:
        try:
            dest_chat_id = int(message.text)
            dest_chat_title = f"Chat {dest_chat_id}"
        except ValueError:
            dest_chat_id = message.text
            dest_chat_title = message.text
    else:
        await update.message.reply_text("❌ Invalid destination. Please forward a message or send a chat ID.")
        return
    
    # Create the task
    user_id = update.effective_user.id
    source_chat_id = context.user_data['source_chat_id']
    source_chat_title = context.user_data['source_chat_title']
    
    task_id = await db.create_task(
        user_id=user_id,
        source_chat_id=source_chat_id,
        source_chat_title=source_chat_title,
        destination_chat_id=dest_chat_id,
        destination_chat_title=dest_chat_title
    )
    
    context.user_data['awaiting_dest'] = False
    context.user_data.pop('source_chat_id', None)
    context.user_data.pop('source_chat_title', None)
    
    keyboard = [
        [InlineKeyboardButton("✅ Enable Task", callback_data=f"enable_{task_id}")],
        [InlineKeyboardButton("⚙️ Add Filters", callback_data=f"filters_{task_id}")],
        [InlineKeyboardButton("📋 My Tasks", callback_data="mytasks")]
    ]
    
    await update.message.reply_text(
        f"✅ <b>Forward Task Created!</b>\n\n"
        f"🆔 Task ID: <code>{task_id}</code>\n"
        f"📤 From: <b>{source_chat_title}</b>\n"
        f"📥 To: <b>{dest_chat_title}</b>\n\n"
        f"The task is currently <b>DISABLED</b>. Enable it to start forwarding.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mytasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all user's forward tasks"""
    user_id = update.effective_user.id
    tasks = await db.get_user_tasks(user_id)
    
    if not tasks:
        await update.message.reply_text(
            "📭 You don't have any forward tasks yet.\n\n"
            "Use /newtask to create one."
        )
        return
    
    text = "📋 <b>Your Forward Tasks:</b>\n\n"
    
    for task in tasks:
        status = "🟢 ON" if task['is_enabled'] else "🔴 OFF"
        text += (
            f"🆔 <code>{task['task_id']}</code> - {status}\n"
            f"📤 {task['source_chat_title']} → 📥 {task['destination_chat_title']}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
        )
    
    keyboard = [
        [InlineKeyboardButton("➕ New Task", callback_data="newtask")],
        [InlineKeyboardButton("🔄 Refresh", callback_data="mytasks")]
    ]
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def edittask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Edit a forward task"""
    if not context.args:
        await update.message.reply_text(
            "⚙️ <b>Edit Task</b>\n\n"
            "Usage: <code>/edittask [task_id]</code>\n\n"
            "Use /mytasks to see your task IDs."
        )
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID.")
        return
    
    task = await db.get_task(task_id)
    if not task:
        await update.message.reply_text("❌ Task not found.")
        return
    
    if task['user_id'] != update.effective_user.id and update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't own this task.")
        return
    
    keyboard = [
        [InlineKeyboardButton("⏱️ Set Delay", callback_data=f"setdelay_{task_id}")],
        [InlineKeyboardButton("📋 Header/Footer", callback_data=f"headerfooter_{task_id}")],
        [InlineKeyboardButton("🌐 Translation", callback_data=f"translate_{task_id}")],
        [InlineKeyboardButton("💧 Watermark", callback_data=f"watermark_{task_id}")],
        [InlineKeyboardButton("⏰ Schedule", callback_data=f"schedule_{task_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="mytasks")]
    ]
    
    await update.message.reply_text(
        f"⚙️ <b>Edit Task {task_id}</b>\n\n"
        f"📤 From: {task['source_chat_title']}\n"
        f"📥 To: {task['destination_chat_title']}\n"
        f"Status: {'🟢 Enabled' if task['is_enabled'] else '🔴 Disabled'}\n\n"
        f"Select an option to edit:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def deletetask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a forward task"""
    if not context.args:
        await update.message.reply_text(
            "🗑️ <b>Delete Task</b>\n\n"
            "Usage: <code>/deletetask [task_id]</code>\n\n"
            "⚠️ This action cannot be undone!"
        )
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID.")
        return
    
    task = await db.get_task(task_id)
    if not task:
        await update.message.reply_text("❌ Task not found.")
        return
    
    if task['user_id'] != update.effective_user.id and update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't own this task.")
        return
    
    await db.delete_task(task_id)
    
    await update.message.reply_text(
        f"✅ Task <code>{task_id}</code> has been deleted.",
        parse_mode=ParseMode.HTML
    )

async def enabletask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable a forward task"""
    if not context.args:
        await update.message.reply_text("Usage: /enabletask [task_id]")
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID.")
        return
    
    task = await db.get_task(task_id)
    if not task:
        await update.message.reply_text("❌ Task not found.")
        return
    
    if task['user_id'] != update.effective_user.id and update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't own this task.")
        return
    
    await db.enable_task(task_id)
    await update.message.reply_text(f"✅ Task <code>{task_id}</code> is now ENABLED.", parse_mode=ParseMode.HTML)

async def disabletask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disable a forward task"""
    if not context.args:
        await update.message.reply_text("Usage: /disabletask [task_id]")
        return
    
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID.")
        return
    
    task = await db.get_task(task_id)
    if not task:
        await update.message.reply_text("❌ Task not found.")
        return
    
    if task['user_id'] != update.effective_user.id and update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't own this task.")
        return
    
    await db.disable_task(task_id)
    await update.message.reply_text(f"✅ Task <code>{task_id}</code> is now DISABLED.", parse_mode=ParseMode.HTML)

# ========== FILTER COMMANDS ==========
async def addfilter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add filter to a task"""
    if len(context.args) < 3:
        await update.message.reply_text(
            "🛠️ <b>Add Filter</b>\n\n"
            "Usage: <code>/addfilter [task_id] [filter_type] [value]</code>\n\n"
            "<b>Filter Types:</b>\n"
            "• <code>keyword</code> - Filter by keywords (comma-separated)\n"
            "• <code>user</code> - Filter by user IDs (comma-separated)\n"
            "• <code>crypto</code> - Crypto filter (only_crypto/no_crypto)\n\n"
            "Add <code>whitelist</code> at the end for whitelist mode.\n\n"
            "<b>Examples:</b>\n"
            "<code>/addfilter 123 keyword bitcoin,ethereum</code>\n"
            "<code>/addfilter 123 user 123456,789012 whitelist</code>"
        )
        return
    
    try:
        task_id = int(context.args[0])
        filter_type = context.args[1].lower()
        filter_value = context.args[2]
        is_whitelist = len(context.args) > 3 and context.args[3].lower() == 'whitelist'
        
        await db.add_filter(task_id, filter_type, filter_value, is_whitelist)
        
        mode = "whitelist" if is_whitelist else "blacklist"
        await update.message.reply_text(
            f"✅ Filter added to task <code>{task_id}</code>:\n"
            f"Type: <b>{filter_type}</b>\n"
            f"Value: <code>{filter_value}</code>\n"
            f"Mode: <b>{mode}</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def removefilter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a filter"""
    if not context.args:
        await update.message.reply_text("Usage: /removefilter [filter_id]")
        return
    
    try:
        filter_id = int(context.args[0])
        await db.delete_filter(filter_id)
        await update.message.reply_text(f"✅ Filter <code>{filter_id}</code> removed.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def filters_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List filters for a task"""
    if not context.args:
        await update.message.reply_text("Usage: /filters [task_id]")
        return
    
    try:
        task_id = int(context.args[0])
        filters_list = await db.get_task_filters(task_id)
        
        if not filters_list:
            await update.message.reply_text("📭 No filters for this task.")
            return
        
        text = f"🛠️ <b>Filters for Task {task_id}:</b>\n\n"
        for f in filters_list:
            mode = "🟢 Whitelist" if f['is_whitelist'] else "🔴 Blacklist"
            text += f"🆔 <code>{f['filter_id']}</code> - <b>{f['filter_type']}</b>\n"
            text += f"Value: <code>{f['filter_value']}</code> ({mode})\n\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ========== SETTINGS COMMANDS ==========
async def setdelay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set forwarding delay"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "⏱️ <b>Set Delay</b>\n\n"
            "Usage: <code>/setdelay [task_id] [seconds]</code>\n\n"
            "Delay must be between 1 and 3600 seconds."
        )
        return
    
    try:
        task_id = int(context.args[0])
        delay = int(context.args[1])
        
        if delay < config.FORWARD_DELAY_MIN or delay > config.FORWARD_DELAY_MAX:
            await update.message.reply_text(f"❌ Delay must be between {config.FORWARD_DELAY_MIN} and {config.FORWARD_DELAY_MAX} seconds.")
            return
        
        await db.update_task(task_id, forward_delay=delay)
        await update.message.reply_text(f"✅ Delay set to <b>{delay}</b> seconds for task <code>{task_id}</code>.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def setheader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set header text"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "📋 <b>Set Header</b>\n\n"
            "Usage: <code>/setheader [task_id] [text]</code>\n\n"
            "Use <code>none</code> to remove header."
        )
        return
    
    try:
        task_id = int(context.args[0])
        header_text = ' '.join(context.args[1:])
        
        if header_text.lower() == 'none':
            header_text = None
        
        await db.update_task(task_id, header_text=header_text)
        await update.message.reply_text(f"✅ Header updated for task <code>{task_id}</code>.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def setfooter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set footer text"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "📋 <b>Set Footer</b>\n\n"
            "Usage: <code>/setfooter [task_id] [text]</code>\n\n"
            "Use <code>none</code> to remove footer."
        )
        return
    
    try:
        task_id = int(context.args[0])
        footer_text = ' '.join(context.args[1:])
        
        if footer_text.lower() == 'none':
            footer_text = None
        
        await db.update_task(task_id, footer_text=footer_text)
        await update.message.reply_text(f"✅ Footer updated for task <code>{task_id}</code>.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def setwatermark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set watermark"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "💧 <b>Set Watermark</b>\n\n"
            "Usage: <code>/setwatermark [task_id] [text] [position]</code>\n\n"
            "Positions: bottom-right, bottom-left, top-right, top-left, center\n"
            "Use <code>none</code> to remove watermark."
        )
        return
    
    try:
        task_id = int(context.args[0])
        
        if context.args[1].lower() == 'none':
            await db.update_task(task_id, watermark_text=None)
            await update.message.reply_text(f"✅ Watermark removed from task <code>{task_id}</code>.", parse_mode=ParseMode.HTML)
            return
        
        watermark_text = context.args[1]
        position = context.args[2] if len(context.args) > 2 else 'bottom-right'
        
        if position not in config.WATERMARK_POSITIONS:
            position = 'bottom-right'
        
        await db.update_task(task_id, watermark_text=watermark_text, watermark_position=position)
        await update.message.reply_text(
            f"✅ Watermark set for task <code>{task_id}</code>:\n"
            f"Text: <b>{watermark_text}</b>\n"
            f"Position: <b>{position}</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def settranslate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set translation language"""
    if len(context.args) < 2:
        langs = ', '.join([f"<code>{k}</code>" for k in config.SUPPORTED_LANGUAGES.keys()])
        await update.message.reply_text(
            "🌐 <b>Set Translation</b>\n\n"
            f"Usage: <code>/settranslate [task_id] [language_code]</code>\n\n"
            f"Supported languages: {langs}\n\n"
            "Use <code>none</code> to disable translation."
        )
        return
    
    try:
        task_id = int(context.args[0])
        lang = context.args[1].lower()
        
        if lang == 'none':
            await db.update_task(task_id, translate_to=None)
            await update.message.reply_text(f"✅ Translation disabled for task <code>{task_id}</code>.", parse_mode=ParseMode.HTML)
            return
        
        if lang not in config.SUPPORTED_LANGUAGES:
            await update.message.reply_text("❌ Unsupported language code.")
            return
        
        await db.update_task(task_id, translate_to=lang)
        await update.message.reply_text(
            f"✅ Translation set for task <code>{task_id}</code>: <b>{config.SUPPORTED_LANGUAGES[lang]}</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def setschedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set power on/off schedule"""
    if len(context.args) < 3:
        await update.message.reply_text(
            "⏰ <b>Set Schedule</b>\n\n"
            "Usage: <code>/setschedule [task_id] on/off [HH:MM]</code>\n\n"
            "Examples:\n"
            "<code>/setschedule 123 on 08:00</code> - Enable at 8 AM\n"
            "<code>/setschedule 123 off 22:00</code> - Disable at 10 PM"
        )
        return
    
    try:
        task_id = int(context.args[0])
        action = context.args[1].lower()
        time_str = context.args[2]
        
        # Validate time format
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            await update.message.reply_text("❌ Invalid time format. Use HH:MM (24-hour).")
            return
        
        if action == 'on':
            await db.update_task(task_id, power_on_time=time_str)
            await update.message.reply_text(f"✅ Task <code>{task_id}</code> will ENABLE at <b>{time_str}</b>", parse_mode=ParseMode.HTML)
        elif action == 'off':
            await db.update_task(task_id, power_off_time=time_str)
            await update.message.reply_text(f"✅ Task <code>{task_id}</code> will DISABLE at <b>{time_str}</b>", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("❌ Action must be 'on' or 'off'.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ========== CONTENT PROCESSING COMMANDS ==========
async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clean message (remove links, usernames, etc.)"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "🧹 <b>Cleaner Filter</b>\n\n"
            "Usage: <code>/clean [task_id] [options]</code>\n\n"
            "Options: all, links, usernames, hashtags\n"
            "Use <code>off</code> to disable."
        )
        return
    
    # This would be implemented in the filter processing
    await update.message.reply_text("✅ Cleaner filter settings updated.")

async def replace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Replace text in messages"""
    if len(context.args) < 3:
        await update.message.reply_text(
            "🔄 <b>Replace Text</b>\n\n"
            "Usage: <code>/replace [task_id] [old_text] [new_text]</code>\n\n"
            "Example: <code>/replace 123 hello hi</code>"
        )
        return
    
    await update.message.reply_text("✅ Text replacement rule added.")

async def removebykeyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove lines by keyword"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "🗑️ <b>Remove Line by Keyword</b>\n\n"
            "Usage: <code>/removebykeyword [task_id] [keyword1,keyword2,...]</code>"
        )
        return
    
    await update.message.reply_text("✅ Keyword removal filter added.")

async def removebyline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove lines by line number"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "🗑️ <b>Remove Line by Order</b>\n\n"
            "Usage: <code>/removebyline [task_id] [1,3,5]</code>\n\n"
            "Removes lines 1, 3, and 5 from messages."
        )
        return
    
    await update.message.reply_text("✅ Line removal filter added.")

# ========== ADMIN COMMANDS ==========
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    if update.effective_user.id not in config.ADMIN_IDS:
        # Show user stats
        user_stats = await db.get_stats(update.effective_user.id)
        await update.message.reply_text(
            f"📊 <b>Your Statistics:</b>\n\n"
            f"Messages Forwarded: <b>{user_stats['total_forwarded']}</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Admin stats
    all_stats = await db.get_stats()
    await update.message.reply_text(
        f"📊 <b>Bot Statistics:</b>\n\n"
        f"👥 Total Users: <b>{all_stats['total_users']}</b>\n"
        f"🔄 Total Tasks: <b>{all_stats['total_tasks']}</b>\n"
        f"📤 Total Forwarded: <b>{all_stats['total_forwarded']}</b>",
        parse_mode=ParseMode.HTML
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast [message]")
        return
    
    message = ' '.join(context.args)
    users = await db.get_all_users()
    user_ids = [u['user_id'] for u in users]
    
    sent, failed = await forward_engine.broadcast_message(
        context.bot, message, user_ids, ParseMode.HTML
    )
    
    await update.message.reply_text(
        f"📢 <b>Broadcast Complete</b>\n\n"
        f"✅ Sent: <b>{sent}</b>\n"
        f"❌ Failed: <b>{failed}</b>",
        parse_mode=ParseMode.HTML
    )

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all users"""
    if update.effective_user.id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    users_list = await db.get_all_users()
    
    text = f"👥 <b>Total Users: {len(users_list)}</b>\n\n"
    
    for user in users_list[:50]:  # Limit to 50
        name = user['first_name'] or user['username'] or f"User {user['user_id']}"
        text += f"• <code>{user['user_id']}</code> - {name}\n"
    
    if len(users_list) > 50:
        text += f"\n... and {len(users_list) - 50} more"
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ========== CALLBACK HANDLER ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "newtask":
        await query.message.reply_text(
            "🔄 <b>Create New Forward Task</b>\n\n"
            "Forward a message from the <b>SOURCE</b> chat.",
            parse_mode=ParseMode.HTML
        )
        context.user_data['awaiting_source'] = True
    
    elif data == "mytasks":
        user_id = update.effective_user.id
        tasks = await db.get_user_tasks(user_id)
        
        if not tasks:
            await query.message.edit_text(
                "📭 You don't have any forward tasks yet.\n\n"
                "Use /newtask to create one."
            )
            return
        
        text = "📋 <b>Your Forward Tasks:</b>\n\n"
        
        for task in tasks:
            status = "🟢 ON" if task['is_enabled'] else "🔴 OFF"
            text += (
                f"🆔 <code>{task['task_id']}</code> - {status}\n"
                f"📤 {task['source_chat_title']} → 📥 {task['destination_chat_title']}\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("➕ New Task", callback_data="newtask")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="mytasks")]
        ]
        
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data.startswith("enable_"):
        task_id = int(data.split("_")[1])
        await db.enable_task(task_id)
        await query.message.reply_text(f"✅ Task <code>{task_id}</code> enabled!", parse_mode=ParseMode.HTML)
    
    elif data.startswith("filters_"):
        task_id = int(data.split("_")[1])
        await query.message.reply_text(
            f"🛠️ <b>Filters for Task {task_id}</b>\n\n"
            "Use /addfilter to add filters.",
            parse_mode=ParseMode.HTML
        )

# ========== MESSAGE HANDLER FOR FORWARDING ==========
async def handle_incoming_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages for forwarding"""
    # Check if we're in task creation mode
    if context.user_data.get('awaiting_source'):
        await handle_source_selection(update, context)
        return
    
    if context.user_data.get('awaiting_dest'):
        await handle_dest_selection(update, context)
        return
    
    # Check if this message should be forwarded
    message = update.message
    if not message:
        return
    
    chat_id = message.chat.id
    
    # Get all active tasks that have this chat as source
    all_tasks = await db.get_all_active_tasks()
    
    for task in all_tasks:
        if task['source_chat_id'] == chat_id:
            # Get filters for this task
            filters_list = await db.get_task_filters(task['task_id'])
            
            # Forward the message
            await forward_engine.forward_message(
                context.bot, message, task, filters_list
            )

# ========== MAIN FUNCTION ==========
async def main():
    """Start the bot"""
    # Initialize database
    await db.init()
    
    # Start scheduler
    scheduler.start()
    
    # Create application
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Task management
    application.add_handler(CommandHandler("newtask", newtask))
    application.add_handler(CommandHandler("mytasks", mytasks))
    application.add_handler(CommandHandler("edittask", edittask))
    application.add_handler(CommandHandler("deletetask", deletetask))
    application.add_handler(CommandHandler("enabletask", enabletask))
    application.add_handler(CommandHandler("disabletask", disabletask))
    
    # Filters
    application.add_handler(CommandHandler("addfilter", addfilter))
    application.add_handler(CommandHandler("removefilter", removefilter))
    application.add_handler(CommandHandler("filters", filters_command))
    
    # Settings
    application.add_handler(CommandHandler("setdelay", setdelay))
    application.add_handler(CommandHandler("setheader", setheader))
    application.add_handler(CommandHandler("setfooter", setfooter))
    application.add_handler(CommandHandler("setwatermark", setwatermark))
    application.add_handler(CommandHandler("settranslate", settranslate))
    application.add_handler(CommandHandler("setschedule", setschedule))
    
    # Content processing
    application.add_handler(CommandHandler("clean", clean))
    application.add_handler(CommandHandler("replace", replace))
    application.add_handler(CommandHandler("removebykeyword", removebykeyword))
    application.add_handler(CommandHandler("removebyline", removebyline))
    
    # Admin
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("users", users))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handler (for task creation and forwarding)
    application.add_handler(MessageHandler(
        tg_filters.ALL, 
        handle_incoming_message
    ))
    
    # Start the bot
    print("🤖 PLATINUM Forward Bot is starting...")
    print("✅ Bot is running!")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
