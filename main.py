"""here is the proof"""
"""
Telegram Forward Bot - PLATINUM Edition
Main Bot File with All Commands
"""
import asyncio
import logging
import re # Import re module for regex operations
import uvicorn
from api import app as fastapi_app
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
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

# Conversation states for task creation and editing
# Added states for filter management and regex filter specifics
STATE_AWAITING_SOURCE, STATE_AWAITING_DEST, STATE_MANAGE_FILTERS, \
STATE_ADD_FILTER_TYPE, STATE_ADD_FILTER_VALUE, STATE_ADD_FILTER_MODE, \
STATE_ADD_REGEX_VALUE = range(7) # Added STATE_ADD_REGEX_VALUE, though not strictly needed for this change yet

# ========== START & HELP ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Modern Start command with Onboarding Wizard"""
    user = update.effective_user
    
    # Add user to database if they are new
    await db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 Quick Start Wizard", callback_data="guide_1")],
        [InlineKeyboardButton("📱 Open Mini App Dashboard", web_app=WebAppInfo(url="https://autoforwardbot-0ub6.onrender.com"))],
        [InlineKeyboardButton("➕ Create New Task", callback_data="newtask")],
        [InlineKeyboardButton("📋 My Tasks", callback_data="mytasks"), InlineKeyboardButton("📊 My Stats", callback_data="stats_user")],
        [InlineKeyboardButton("❓ Help Center", callback_data="help_main")]
    ]
    
    welcome_text = (
        f"👋 <b>Welcome to PLATINUM Forwarder, {user.first_name}!</b>\n\n"
        "The most powerful tool to sync content between Telegram channels and groups.\n\n"
        "✨ <b>First time here?</b> Tap the button below for a 30-second tour!"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            welcome_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            welcome_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Categorized Help System"""
    keyboard = [
        [InlineKeyboardButton("📤 Forwarding Guide", callback_data="help_forward"), InlineKeyboardButton("🛠️ Filters", callback_data="help_filters")],
        [InlineKeyboardButton("💧 Watermarks", callback_data="help_watermark"), InlineKeyboardButton("🌐 Translation", callback_data="help_trans")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="start_menu")]
    ]
    
    help_text = (
        "❓ <b>How can we help you today?</b>\n\n"
        "Select a category below to learn more about specific features."
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(help_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

# ========== ONBOARDING GUIDE STEPS ==========
async def onboarding_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the multi-step interactive guide"""
    query = update.callback_query
    await query.answer()
    
    step = int(query.data.split("_")[1])
    
    if step == 1:
        text = (
            "🚀 <b>Step 1: The Basics</b>\n\n"
            "To forward messages, you need a <b>Source</b> (where messages come from) and a <b>Destination</b> (where they go).\n\n"
            "💡 <i>Tip: The bot must be an Admin in the destination to post messages!</i>"
        )
        keyboard = [[InlineKeyboardButton("Next: Adding Chats ➡️", callback_data="guide_2")]]
        
    elif step == 2:
        text = (
            "📂 <b>Step 2: Selecting Chats</b>\n\n"
            "When you create a task, you can simply <b>forward a message</b> from the chat to the bot.\n\n"
            "The bot will automatically detect the Chat ID and Title. No typing required!"
        )
        keyboard = [
            [InlineKeyboardButton("⬅️ Back", callback_data="guide_1")],
            [InlineKeyboardButton("Next: Pro Features ➡️", callback_data="guide_3")]
        ]
        
    elif step == 3:
        text = (
            "✨ <b>Step 3: Pro Customization</b>\n\n"
            "Once a task is created, use <b>Edit Task</b> to:\n"
            "• Add Watermarks 💧\n"
            "• Auto-Translate 🌐\n"
            "• Filter keywords or users 🛠️\n\n"
            "Ready to try?"
        )
        keyboard = [
            [InlineKeyboardButton("⬅️ Back", callback_data="guide_2")],
            [InlineKeyboardButton("🚀 Create My First Task", callback_data="newtask")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="start_menu")]
        ]
        
    await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))


# ========== FORWARD TASK MANAGEMENT ==========
async def newtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new forward task with interactive selection"""
    user_id = update.effective_user.id
    
    # Get recent sources for quick selection
    recent_sources = await db.get_recent_sources(user_id)
    
    text = (
        "🔄 <b>Create New Forward Task</b>\n\n"
        "<b>Step 1: Select Source Chat</b>\n"
        "Choose from recent chats or forward a message from a new source."
    )
    
    keyboard = []
    # Add recent sources as buttons
    for src in recent_sources:
        title = src['source_chat_title'] or str(src['source_chat_id'])
        # Truncate title if too long
        if len(title) > 20: title = title[:17] + "..."
        keyboard.append([InlineKeyboardButton(f"📂 {title}", callback_data=f"select_source_{src['source_chat_id']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    context.user_data['awaiting_source'] = True
    context.user_data['awaiting_dest'] = False
    return STATE_AWAITING_SOURCE

async def handle_source_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle source chat selection (Message or Callback)"""
    source_chat_id = None
    source_chat_title = "Unknown"
    
    # Handle Callback Query (Button Selection)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data.startswith("select_source_"):
            try:
                source_chat_id = int(data.split("_")[2])
                # Ideally fetch title from DB or known cache, defaulting to ID for now
                # We could do a quick DB lookup if needed, but let's trust the ID.
                # Or re-fetch recent to get title? Let's use ID as title fallback.
                source_chat_title = f"Chat {source_chat_id}"
                # Try to find title in recent list if possible
                recent = await db.get_recent_sources(update.effective_user.id, limit=20)
                for r in recent:
                    if int(r['source_chat_id']) == source_chat_id:
                        source_chat_title = r['source_chat_title']
                        break
            except ValueError:
                await query.message.edit_text("❌ Invalid selection.")
                return STATE_AWAITING_SOURCE
    
    # Handle Message Forwarding
    elif update.message:
        message = update.message
        if message.forward_from_chat:
            source_chat_id = message.forward_from_chat.id
            source_chat_title = message.forward_from_chat.title or "Unknown"
        elif message.text:
            try:
                source_chat_id = int(message.text)
                source_chat_title = f"Chat {source_chat_id}"
            except ValueError:
                # Support username (e.g. @channel)
                source_chat_id = message.text
                source_chat_title = message.text
        else:
             await update.message.reply_text("❌ Invalid source. Please forward a message or select from the list.")
             return STATE_AWAITING_SOURCE

    if not source_chat_id:
        return STATE_AWAITING_SOURCE

    context.user_data['source_chat_id'] = source_chat_id
    context.user_data['source_chat_title'] = source_chat_title
    context.user_data['awaiting_source'] = False
    context.user_data['awaiting_dest'] = True
    
    # Prepare Step 2: Destination Selection
    user_id = update.effective_user.id
    recent_dests = await db.get_recent_destinations(user_id)
    
    text = (
        f"✅ Source: <b>{source_chat_title}</b>\n\n"
        "<b>Step 2: Select Destination Chat</b>\n"
        "Choose from recent chats or forward a message from a new destination."
    )
    
    keyboard = []
    for dst in recent_dests:
        # Don't show the selected source as a destination option (prevent loop)
        if str(dst['destination_chat_id']) == str(source_chat_id):
            continue
            
        title = dst['destination_chat_title'] or str(dst['destination_chat_id'])
        if len(title) > 20: title = title[:17] + "..."
        keyboard.append([InlineKeyboardButton(f"📥 {title}", callback_data=f"select_dest_{dst['destination_chat_id']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

    if update.callback_query:
         await update.callback_query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    return STATE_AWAITING_DEST

async def handle_dest_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle destination chat selection (Message or Callback)"""
    dest_chat_id = None
    dest_chat_title = "Unknown"
    
    # Handle Callback Query
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        data = query.data
        
        if data.startswith("select_dest_"):
            try:
                dest_chat_id = int(data.split("_")[2])
                dest_chat_title = f"Chat {dest_chat_id}"
                # Try to fetch real title
                recent = await db.get_recent_destinations(update.effective_user.id, limit=20)
                for r in recent:
                    if int(r['destination_chat_id']) == dest_chat_id:
                        dest_chat_title = r['destination_chat_title']
                        break
            except ValueError:
                await query.message.edit_text("❌ Invalid selection.")
                return STATE_AWAITING_DEST

    # Handle Message Forwarding
    elif update.message:
        message = update.message
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
            await update.message.reply_text("❌ Invalid destination. Please forward a message or select from the list.")
            return STATE_AWAITING_DEST

    if not dest_chat_id:
        return STATE_AWAITING_DEST

    # Create the task
    user_id = update.effective_user.id
    source_chat_id = context.user_data['source_chat_id']
    source_chat_title = context.user_data['source_chat_title']
    
    # Check for self-forwarding loop
    if str(source_chat_id) == str(dest_chat_id):
        error_text = "❌ Source and Destination cannot be the same."
        if update.callback_query:
            await update.callback_query.message.reply_text(error_text)
        else:
            await update.message.reply_text(error_text)
        return STATE_AWAITING_DEST

    task_id = await db.create_task(
        user_id=user_id,
        source_chat_id=source_chat_id,
        source_chat_title=source_chat_title,
        destination_chat_id=dest_chat_id,
        destination_chat_title=dest_chat_title
    )
    
    # Clear temporary data
    context.user_data.pop('source_chat_id', None)
    context.user_data.pop('source_chat_title', None)
    context.user_data.pop('awaiting_source', None)
    context.user_data.pop('awaiting_dest', None)
    
    keyboard = [
        [InlineKeyboardButton("✅ Enable Task", callback_data=f"enable_{task_id}")],
        [InlineKeyboardButton("⚙️ Configure Task", callback_data=f"edittask_{task_id}")],
        [InlineKeyboardButton("📋 My Tasks", callback_data="mytasks")]
    ]
    
    success_text = (
        f"✅ <b>Task Created!</b>\n\n"
        f"📤 <b>From:</b> {source_chat_title}\n"
        f"📥 <b>To:</b> {dest_chat_title}\n\n"
        f"Task ID: <code>{task_id}</code>"
    )

    if update.callback_query:
        await update.callback_query.message.edit_text(
            success_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            success_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return ConversationHandler.END
    
    await update.message.reply_text(
        f"✅ <b>Forward Task Created!</b>\n\n"
        f"🆔 Task ID: <code>{task_id}</code>\n"
        f"📤 From: <b>{source_chat_title}</b>\n"
        f"📥 To: <b>{dest_chat_title}</b>\n\n"
        f"The task is currently <b>DISABLED</b>. Use the options below to configure it.",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END # End conversation after task creation


async def mytasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all user's forward tasks"""
    query = update.callback_query
    user_id = update.effective_user.id
    tasks = await db.get_user_tasks(user_id)
    
    if not tasks:
        text = "📭 You don't have any forward tasks yet.\n\nUse /newtask to create one."
        keyboard = [[InlineKeyboardButton("➕ New Task", callback_data="newtask")]]
        if query:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    text = "📋 <b>Your Forward Tasks:</b>\n\n"
    keyboard = []
    for task in tasks:
        status = "🟢 ON" if task['is_enabled'] else "🔴 OFF"
        text += (
            f"🆔 <code>{task['task_id']}</code> - {status}\n"
            f"📤 {task['source_chat_title']} → 📥 {task['destination_chat_title']}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
        )
        keyboard.append([InlineKeyboardButton(f"⚙️ Edit Task {task['task_id']}", callback_data=f"edittask_{task['task_id']}")])
    
    keyboard.append([InlineKeyboardButton("➕ New Task", callback_data="newtask")])
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="start_menu")])
    
    if query:
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

async def edittask_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the edit task menu (Supports command and callback)"""
    query = update.callback_query
    task_id = None

    if query:
        # data format: edittask_[id]
        try:
            task_id = int(query.data.split("_")[1])
        except (IndexError, ValueError):
            pass
    elif context.args:
        try:
            task_id = int(context.args[0])
        except ValueError:
            pass

    if not task_id:
        task_id = context.user_data.get('editing_task_id')

    if not task_id:
        text = "⚙️ <b>Edit Task</b>\n\nUsage: <code>/edittask [task_id]</code>\n\nUse /mytasks to see your task IDs."
        if query: await query.message.edit_text(text, parse_mode=ParseMode.HTML)
        else: await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        return
    
    task = await db.get_task(task_id)
    if not task:
        if query: await query.message.edit_text("❌ Task not found.")
        else: await update.message.reply_text("❌ Task not found.")
        return
    
    user_id = update.effective_user.id
    if task['user_id'] != user_id and user_id not in config.ADMIN_IDS:
        if query: await query.message.edit_text("❌ You don't own this task.")
        else: await update.message.reply_text("❌ You don't own this task.")
        return
    
    context.user_data['editing_task_id'] = task_id

    # Determine status indicators
    status_emoji = "🟢" if task['is_enabled'] else "🔴"
    status_text = "Enabled" if task['is_enabled'] else "Disabled"
    
    # Format labels with current values
    delay_val = f"{task['forward_delay']}s" if task['forward_delay'] > 0 else "Off"
    translate_val = task['translate_to'].upper() if task['translate_to'] and task['translate_to'] != 'none' else "Off"
    watermark_val = "On" if task['watermark_text'] and task['watermark_text'] != 'none' else "Off"

    keyboard = [
        [
            InlineKeyboardButton(f"⏱️ Delay: {delay_val}", callback_data=f"edit_delay_{task_id}"),
            InlineKeyboardButton(f"🌐 Trans: {translate_val}", callback_data=f"edit_translate_{task_id}")
        ],
        [
            InlineKeyboardButton(f"📋 Header/Footer", callback_data=f"edit_headerfooter_{task_id}"),
            InlineKeyboardButton(f"💧 Watermark: {watermark_val}", callback_data=f"edit_watermark_{task_id}")
        ],
        [
            InlineKeyboardButton(f"⏰ Schedule", callback_data=f"edit_schedule_{task_id}"),
            InlineKeyboardButton(f"🛠️ Manage Filters", callback_data=f"manage_filters_{task_id}")
        ],
        [
            InlineKeyboardButton(f"{status_emoji} {status_text}", callback_data=f"enable_{task_id}" if not task['is_enabled'] else f"disable_{task_id}"),
            InlineKeyboardButton("🗑️ Delete Task", callback_data=f"deletetask_confirm_{task_id}")
        ],
        [InlineKeyboardButton("🔙 Back to My Tasks", callback_data="mytasks")]
    ]
    
    text = (
        f"⚙️ <b>Task Configuration: {task_id}</b>\n\n"
        f"<b>Source:</b> <code>{task['source_chat_title']}</code>\n"
        f"<b>Dest:</b> <code>{task['destination_chat_title']}</code>\n"
        f"<b>Status:</b> {status_emoji} {status_text}\n\n"
        f"<i>Select a setting to modify:</i>"
    )

    if query:
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))

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
    
    user_id = update.effective_user.id
    if task['user_id'] != user_id and user_id not in config.ADMIN_IDS:
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
    
    user_id = update.effective_user.id
    if task['user_id'] != user_id and user_id not in config.ADMIN_IDS:
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
    
    user_id = update.effective_user.id
    if task['user_id'] != user_id and user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't own this task.")
        return
    
    await db.disable_task(task_id)
    await update.message.reply_text(f"✅ Task <code>{task_id}</code> is now DISABLED.", parse_mode=ParseMode.HTML)

# ========== FILTER COMMANDS ==========

# Helper to get task and check ownership
async def get_task_or_deny(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    task = await db.get_task(task_id)
    if not task:
        await update.message.reply_text("❌ Task not found.")
        return None
    
    user_id = update.effective_user.id
    if task['user_id'] != user_id and user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You don't own this task.")
        return None
    return task

async def addfilter_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the add filter conversation. Prompts for filter type."""
    # This command is entry point for '/addfilter [task_id]'
    # It should be called from command handler, not callback for state management.
    # Re-structuring this to be triggered by /addfilter command.
    # For now, let's assume it's called via callback from edittask_menu.
    
    task_id = context.user_data.get('current_task_id') # Get from user_data set by edittask_menu
    if not task_id:
        await update.message.reply_text("❌ Error: No task selected. Please use `/edittask [task_id]` first.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("🔑 Keyword", callback_data="filtertype_keyword")],
        [InlineKeyboardButton("✨ Regex", callback_data="filtertype_regex")], # New option for Regex
        [InlineKeyboardButton("👤 User ID", callback_data="filtertype_user")],
        [InlineKeyboardButton("📈 Crypto", callback_data="filtertype_crypto")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"edittask_{task_id}")]
    ]
    await update.message.reply_text(
        f"Select the type of filter to add for task <code>{task_id}</code>:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return STATE_ADD_FILTER_TYPE

async def addfilter_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle selection of filter type via callback"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split("_")
    if len(data_parts) < 2 or data_parts[0] != "filtertype":
        await query.message.reply_text("❌ Invalid callback data.")
        return ConversationHandler.END
        
    filter_type = data_parts[1] # e.g., "keyword", "regex"
    task_id = context.user_data.get('current_task_id')

    if not task_id:
        await query.message.reply_text("❌ Internal error: Task ID not found. Please restart the add filter process.")
        return ConversationHandler.END

    context.user_data['new_filter_type'] = filter_type
    
    prompt_text = f"Enter the value for the '{filter_type}' filter.\n\n"
    if filter_type == 'keyword':
        prompt_text += "Use comma-separated terms."
    elif filter_type == 'regex':
        prompt_text += "Enter a valid regex pattern. \n(Example: `(?i)chapter \d+` for case-insensitive chapter numbers)" # Added example
    elif filter_type == 'user':
        prompt_text += "Use comma-separated Telegram User IDs."
    elif filter_type == 'crypto':
        prompt_text += "Use 'only_crypto' or 'no_crypto'."
    else:
        prompt_text += "Enter the filter value."
        
    keyboard = [
        [InlineKeyboardButton("🔙 Cancel", callback_data=f"manage_filters_{task_id}")]
    ]
    await query.message.edit_text(prompt_text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_ADD_FILTER_VALUE

async def addfilter_value_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle input of filter value via message, then ask for mode"""
    filter_value = update.message.text
    context.user_data['new_filter_value'] = filter_value
    
    task_id = context.user_data.get('current_task_id')
    if not task_id:
        await update.message.reply_text("❌ Internal error: Task ID not found. Please restart the add filter process.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("⚪ Blacklist (default)", callback_data="filtermode_blacklist")],
        [InlineKeyboardButton("🟢 Whitelist", callback_data="filtermode_whitelist")],
        [InlineKeyboardButton("🔙 Cancel", callback_data=f"manage_filters_{task_id}")]
    ]
    await update.message.reply_text("Select the mode for this filter:", reply_markup=InlineKeyboardMarkup(keyboard))
    return STATE_ADD_FILTER_MODE

async def addfilter_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle selection of filter mode via callback and save filter"""
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split("_")
    if len(data_parts) < 2 or data_parts[0] != "filtermode":
        await query.message.reply_text("❌ Invalid callback data.")
        return ConversationHandler.END
        
    mode = data_parts[1] # "blacklist" or "whitelist"
    is_whitelist = (mode == "whitelist")
    
    task_id = context.user_data.get('current_task_id')
    filter_type = context.user_data.get('new_filter_type')
    filter_value = context.user_data.get('new_filter_value')
    
    if not all([task_id, filter_type, filter_value]):
        await query.message.reply_text("❌ Internal error: Missing filter details. Please restart the add filter process.")
        return ConversationHandler.END

    try:
        await db.add_filter(task_id, filter_type, filter_value, is_whitelist)
        
        mode_display = "🟢 Whitelist" if is_whitelist else "🔴 Blacklist"
        await query.message.reply_text(
            f"✅ Filter added to task <code>{task_id}</code>:\n"
            f"Type: <b>{filter_type.capitalize()}</b>\n"
            f"Value: <code>{filter_value}</code>\n"
            f"Mode: {mode_display}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await query.message.reply_text(f"❌ Error adding filter: {str(e)}")
        
    # Clean up user data
    context.user_data.pop('current_task_id', None)
    context.user_data.pop('new_filter_type', None)
    context.user_data.pop('new_filter_value', None)

    return ConversationHandler.END # End conversation after filter is added


async def removefilter_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles callback or command for removing filters (requires filter_id)"""
    query = update.callback_query

    filter_id = None
    if query:
        await query.answer()
        data_parts = query.data.split("_")
        if len(data_parts) >= 2 and data_parts[0] == "removefilter":
            try:
                filter_id = int(data_parts[1])
            except ValueError:
                pass
    else:
        # Command version: /removefilter [filter_id]
        if context.args:
            try:
                filter_id = int(context.args[0])
            except ValueError:
                pass

    if filter_id is None:
        message = "❌ Invalid filter ID. Please provide a number.\nUsage: `/removefilter [filter_id]`"
        if query:
            await query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return ConversationHandler.END

    try:
        await db.delete_filter(filter_id)
        message = f"✅ Filter <code>{filter_id}</code> removed."
        if query:
            await query.message.reply_text(message, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    except Exception as e:
        message = f"❌ Error removing filter: {str(e)}"
        if query:
            await query.message.reply_text(message)
        else:
            await update.message.reply_text(message)
        return ConversationHandler.END

    # After removal, try to go back to manage filters if possible
    task_id = context.user_data.get('current_task_id')
    if task_id:
        # If it was a callback, we can show the menu again
        if query:
            return await manage_filters_menu(update, context)
        else:
            await update.message.reply_text(f"You can view updated filters with `/filters {task_id}`")

    return ConversationHandler.END

async def filters_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /filters command to list filters for a task."""
    if not context.args:
        await update.message.reply_text(
            "🛠️ <b>List Filters</b>\n\n"
            "Usage: <code>/filters [task_id]</code>\n\n"
            "This will show all filters applied to a specific task."
        )
        return
    
    try:
        task_id = int(context.args[0])
        task = await get_task_or_deny(update, context, task_id)
        if not task:
            return # Error message already sent by get_task_or_deny

        filters_list = await db.get_task_filters(task_id)
        
        if not filters_list:
            keyboard = [
                [InlineKeyboardButton("➕ Add Filter", callback_data=f"addfilter_{task_id}")],
                [InlineKeyboardButton("🔙 Back to Edit Task", callback_data=f"edittask_{task_id}")]
            ]
            await update.message.reply_text("📭 No filters for this task.", reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        text = f"🛠️ <b>Filters for Task {task_id}:</b>\n\n"
        for f in filters_list:
            mode = "🟢 Whitelist" if f['is_whitelist'] else "🔴 Blacklist"
            # Display filter type clearly
            text += f"🆔 <code>{f['filter_id']}</code> - <b>{f['filter_type'].capitalize()}</b>\n"
            text += f"Value: <code>{f['filter_value']}</code> ({mode})\n\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Filter", callback_data=f"addfilter_{task_id}")],
            # The remove filter button needs a filter_id, which we don't have here easily.
            # For now, /removefilter command is the primary way.
            [InlineKeyboardButton("🔙 Back to Edit Task", callback_data=f"edittask_{task_id}")]
        ]
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID. Please provide a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error listing filters: {str(e)}")

async def manage_filters_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the manage filters menu for a task (callback version)."""
    query = update.callback_query
    
    # Try to get task_id from callback data or user_data
    task_id = None
    if query:
        await query.answer()
        data = query.data
        if data.startswith("manage_filters_"):
            try:
                task_id = int(data.split("_")[2])
            except (IndexError, ValueError):
                pass
        
    if not task_id:
        task_id = context.user_data.get('current_task_id')

    if not task_id:
        if query:
            await query.message.edit_text("❌ Error: Task ID not found. Please use `/edittask [task_id]`.")
        else:
            await update.message.reply_text("❌ Error: Task ID not found. Please use `/edittask [task_id]`.")
        return ConversationHandler.END

    # Set as current task for context
    context.user_data['current_task_id'] = task_id

    try:
        filters_list = await db.get_task_filters(task_id)
        
        text = f"🛠️ <b>Manage Filters for Task {task_id}:</b>\n\n"
        if not filters_list:
            text += "📭 No filters for this task."
        else:
            for f in filters_list:
                mode = "🟢 Whitelist" if f['is_whitelist'] else "🔴 Blacklist"
                text += f"🆔 <code>{f['filter_id']}</code> - <b>{f['filter_type'].capitalize()}</b>\n"
                text += f"Value: <code>{f['filter_value']}</code> ({mode})\n"
                text += f"❌ To remove: <code>/removefilter {f['filter_id']}</code>\n\n"

        keyboard = [
            [InlineKeyboardButton("➕ Add Filter", callback_data=f"addfilter_{task_id}")],
            [InlineKeyboardButton("🔙 Back to Edit Task", callback_data=f"edittask_{task_id}")]
        ]
        
        if query:
            await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
            
        return STATE_MANAGE_FILTERS
    except Exception as e:
        logger.error(f"Error in manage_filters_menu: {e}")
        if query:
            await query.message.reply_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END

# Alias for compatibility with some references
filters_command_callback_handler = manage_filters_menu

# ========== SETTINGS COMMANDS (UPDATED FOR CONTEXT) ==========
async def setdelay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set forwarding delay"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "⏱️ <b>Set Delay</b>\n\n"
            "Usage: <code>/setdelay [task_id] [seconds]</code>\n\n"
            f"Delay must be between {config.FORWARD_DELAY_MIN} and {config.FORWARD_DELAY_MAX} seconds."
        )
        return
    
    try:
        task_id = int(context.args[0])
        delay = int(context.args[1])
        
        if delay < config.FORWARD_DELAY_MIN or delay > config.FORWARD_DELAY_MAX:
            await update.message.reply_text(f"❌ Delay must be between {config.FORWARD_DELAY_MIN} and {config.FORWARD_DELAY_MAX} seconds.")
            return
        
        if not await get_task_or_deny(update, context, task_id):
            return

        await db.update_task(task_id, forward_delay=delay)
        await update.message.reply_text(f"✅ Delay set to <b>{delay} seconds</b> for task <code>{task_id}</code>.", parse_mode=ParseMode.HTML)
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID or delay value. Please provide numbers.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting delay: {str(e)}")

async def setheader(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set header text"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "📋 <b>Set Header</b>\n\n"
            "Usage: <code>/setheader [task_id] [text]</code>\n\n"
            "Use <code>none</code> to remove the header."
        )
        return
    
    try:
        task_id = int(context.args[0])
        header_text = ' '.join(context.args[1:])
        
        if header_text.lower() == 'none':
            header_text = None
        
        if not await get_task_or_deny(update, context, task_id):
            return

        await db.update_task(task_id, header_text=header_text)
        await update.message.reply_text(f"✅ Header updated for task <code>{task_id}</code>.", parse_mode=ParseMode.HTML)
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID. Please provide a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting header: {str(e)}")

async def setfooter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set footer text"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "📋 <b>Set Footer</b>\n\n"
            "Usage: <code>/setfooter [task_id] [text]</code>\n\n"
            "Use <code>none</code> to remove the footer."
        )
        return
    
    try:
        task_id = int(context.args[0])
        footer_text = ' '.join(context.args[1:])
        
        if footer_text.lower() == 'none':
            footer_text = None
        
        if not await get_task_or_deny(update, context, task_id):
            return

        await db.update_task(task_id, footer_text=footer_text)
        await update.message.reply_text(f"✅ Footer updated for task <code>{task_id}</code>.", parse_mode=ParseMode.HTML)
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID. Please provide a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting footer: {str(e)}")

async def setwatermark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set watermark"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "💧 <b>Set Watermark</b>\n\n"
            "Usage: <code>/setwatermark [task_id] [text] [position]</code>\n\n"
            "Positions: bottom-right, bottom-left, top-right, top-left, center\n"
            "Use <code>none</code> for the text to remove watermark."
        )
        return
    
    try:
        task_id = int(context.args[0])
        
        if context.args[1].lower() == 'none':
            watermark_text = None
            position = 'bottom-right' # Default position, not used if text is None
        else:
            watermark_text = context.args[1]
            position = context.args[2] if len(context.args) > 2 else 'bottom-right'
        
        if position not in config.WATERMARK_POSITIONS:
            position = 'bottom-right'
        
        if not await get_task_or_deny(update, context, task_id):
            return

        await db.update_task(task_id, watermark_text=watermark_text, watermark_position=position)
        
        if watermark_text is None:
            await update.message.reply_text(f"✅ Watermark removed from task <code>{task_id}</code>.", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(
                f"✅ Watermark set for task <code>{task_id}</code>:\n"
                f"Text: <b>{watermark_text}</b>\n"
                f"Position: <b>{position}</b>",
                parse_mode=ParseMode.HTML
            )
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID. Please provide a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting watermark: {str(e)}")

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
            target_lang = None
        elif lang in config.SUPPORTED_LANGUAGES:
            target_lang = lang
        else:
            await update.message.reply_text("❌ Unsupported language code.")
            return

        if not await get_task_or_deny(update, context, task_id):
            return
            
        await db.update_task(task_id, translate_to=target_lang)
        
        if target_lang is None:
            await update.message.reply_text(f"✅ Translation disabled for task <code>{task_id}</code>.", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(
                f"✅ Translation set for task <code>{task_id}</code>: <b>{config.SUPPORTED_LANGUAGES[target_lang]}</b> ({target_lang})",
                parse_mode=ParseMode.HTML
            )
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID. Please provide a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting translation: {str(e)}")

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
        
        if not await get_task_or_deny(update, context, task_id):
            return
            
        if action == 'on':
            await db.update_task(task_id, power_on_time=time_str)
            await update.message.reply_text(f"✅ Task <code>{task_id}</code> will ENABLE at <b>{time_str}</b>", parse_mode=ParseMode.HTML)
        elif action == 'off':
            await db.update_task(task_id, power_off_time=time_str)
            await update.message.reply_text(f"✅ Task <code>{task_id}</code> will DISABLE at <b>{time_str}</b>", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("❌ Action must be 'on' or 'off'.")
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID or time format. Please provide numbers for task ID and HH:MM for time.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting schedule: {str(e)}")

# ========== CONTENT PROCESSING COMMANDS ==========
async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clean message (remove links, usernames, etc.)"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "🧹 <b>Cleaner Filter</b>\n\n"
            "Usage: <code>/clean [task_id] [options]</code>\n\n"
            "Options: links, usernames, hashtags, mentions\n"
            "Example: <code>/clean 123 links usernames hashtags</code>\n"
            "Use <code>none</code> to disable all cleaner options."
        )
        return
    
    try:
        task_id = int(context.args[0])
        options = context.args[1:]
        
        if not await get_task_or_deny(update, context, task_id):
            return

        # Parse options into a dictionary for cleaner_options
        # This part is currently a placeholder as cleaner_options are hardcoded in filters.py
        # To make this configurable, we'd need to store cleaner options per task in the DB.
        # For now, this command primarily serves as an acknowledgement.
        
        await update.message.reply_text(f"✅ Cleaner filter settings would be updated for task <code>{task_id}</code>. Current implementation uses fixed options.")
        
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID. Please provide a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error processing clean command: {str(e)}")


async def replace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Replace text in messages"""
    if len(context.args) < 3:
        await update.message.reply_text(
            "🔄 <b>Replace Text</b>\n\n"
            "Usage: <code>/replace [task_id] [old_text] [new_text]</code>\n\n"
            "Example: <code>/replace 123 hello hi</code>\n"
            "To remove text, use an empty string for new_text."
        )
        return
    
    try:
        task_id = int(context.args[0])
        old_text = context.args[1]
        new_text = ' '.join(context.args[2:])
        
        if not await get_task_or_deny(update, context, task_id):
            return
            
        # Storing replacement rules is complex. For now, this is a placeholder.
        # A proper implementation would store a list of replacements per task in DB.
        await update.message.reply_text(f"✅ Text replacement rule would be added for task <code>{task_id}</code>.")
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID. Please provide a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting text replacement: {str(e)}")


async def removebykeyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove lines by keyword"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "🗑️ <b>Remove Line by Keyword</b>\n\n"
            "Usage: <code>/removebykeyword [task_id] [keyword1,keyword2,...]</code>\n\n"
            "Example: <code>/removebykeyword 123 spam,ad,free</code>"
        )
        return
    
    try:
        task_id = int(context.args[0])
        keywords = context.args[1].split(',')
        
        if not await get_task_or_deny(update, context, task_id):
            return
            
        # Storing keyword removal rules is complex. Placeholder for now.
        await update.message.reply_text(f"✅ Keyword removal rule would be added for task <code>{task_id}</code>.")
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID. Please provide a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting keyword removal: {str(e)}")

async def removebyline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove lines by line number"""
    if len(context.args) < 2:
        await update.message.reply_text(
            "🗑️ <b>Remove Line by Order</b>\n\n"
            "Usage: <code>/removebyline [task_id] [1,3,5]</code>\n\n"
            "Example: <code>/removebyline 123 1,3,5</code>\n"
            "Removes lines 1, 3, and 5 from messages."
        )
        return
    
    try:
        task_id = int(context.args[0])
        # Parse line numbers, ensuring they are integers and positive
        line_numbers = [int(ln.strip()) for ln in context.args[1].split(',') if ln.strip().isdigit() and int(ln.strip()) > 0]
        
        if not await get_task_or_deny(update, context, task_id):
            return
            
        # Storing line removal rules is complex. Placeholder for now.
        await update.message.reply_text(f"✅ Line removal rule would be added for task <code>{task_id}</code>.")
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID or line numbers. Please provide numbers.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error setting line removal: {str(e)}")

# ========== ADMIN COMMANDS ==========
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    user_id = update.effective_user.id
    
    if user_id not in config.ADMIN_IDS:
        # Show user stats
        user_stats = await db.get_stats(user_id)
        await update.message.reply_text(
            f"📊 <b>Your Statistics:</b>\n\n"
            f"Messages Forwarded: <b>{user_stats.get('total_forwarded', 0)}</b>",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Admin stats
    all_stats = await db.get_stats()
    await update.message.reply_text(
        f"📊 <b>Bot Statistics:</b>\n\n"
        f"👥 Total Users: <b>{all_stats.get('total_users', 0)}</b>\n"
        f"🔄 Total Tasks: <b>{all_stats.get('total_tasks', 0)}</b>\n" # Added default 0 for safety
        f"📤 Total Forwarded: <b>{all_stats.get('total_forwarded', 0)}</b>",
        parse_mode=ParseMode.HTML
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users"""
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast [message]")
        return
    
    message_text = ' '.join(context.args)
    users = await db.get_all_users()
    user_ids = [u['user_id'] for u in users]
    
    sent_count = 0
    failed_count = 0
    
    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=message_text,
                parse_mode=ParseMode.HTML # Assuming broadcasts are HTML formatted
            )
            sent_count += 1
            await asyncio.sleep(0.1) # Small delay to avoid hitting rate limits too quickly
        except Exception as e:
            logger.error(f"Broadcast to user {uid} failed: {e}")
            failed_count += 1
    
    await update.message.reply_text(
        f"📢 <b>Broadcast Complete</b>\n\n"
        f"✅ Sent: <b>{sent_count}</b>\n"
        f"❌ Failed: <b>{failed_count}</b>",
        parse_mode=ParseMode.HTML
    )

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all users"""
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ Admin only command.")
        return
    
    users_list = await db.get_all_users()
    
    text = f"👥 <b>Total Active Users: {len(users_list)}</b>\n\n"
    
    # Display a subset of users for brevity
    for user in users_list[:50]: 
        name = user.get('first_name', '') or user.get('username', '') or f"User {user['user_id']}"
        text += f"• <code>{user['user_id']}</code> - {name}\n"
    
    if len(users_list) > 50:
        text += f"\n... and {len(users_list) - 50} more."
    
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ========== CALLBACK HANDLER ==========
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Handle My Tasks callback
    if data == "mytasks":
        user_id = update.effective_user.id
        tasks = await db.get_user_tasks(user_id)
        
        if not tasks:
            keyboard = [[InlineKeyboardButton("➕ New Task", callback_data="newtask")]]
            await query.message.edit_text(
                "📭 You don't have any forward tasks yet.\n\n"
                "Use /newtask to create one.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        text = "📋 <b>Your Forward Tasks:</b>\n\n"
        keyboard = []
        for task in tasks:
            status = "🟢 ON" if task['is_enabled'] else "🔴 OFF"
            text += (
                f"🆔 <code>{task['task_id']}</code> - {status}\n"
                f"📤 {task['source_chat_title']} → 📥 {task['destination_chat_title']}\n"
                f"➖➖➖➖➖➖➖➖➖➖\n"
            )
            # Add edit button row
            keyboard.append([InlineKeyboardButton(f"⚙️ Edit {task['task_id']}", callback_data=f"edittask_{task['task_id']}")])
        
        keyboard.append([InlineKeyboardButton("➕ New Task", callback_data="newtask")])
        keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="mytasks")])
        
        await query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Handle Enable Task callback
    elif data.startswith("enable_"):
        try:
            task_id = int(data.split("_")[1])
            # Verify task ownership or admin status before enabling
            task = await db.get_task(task_id)
            if not task:
                await query.message.reply_text("❌ Task not found.")
                return
            user_id = query.from_user.id
            if task['user_id'] != user_id and user_id not in config.ADMIN_IDS:
                await query.message.reply_text("❌ You don't own this task.")
                return
            
            await db.enable_task(task_id)
            # Check if we are in the edit menu context (to refresh it)
            if "edittask" in str(query.message.reply_markup): # Crude check or just call edittask_menu
                await edittask_menu(update, context)
            else:
                 await query.message.reply_text(f"✅ Task <code>{task_id}</code> enabled!", parse_mode=ParseMode.HTML)
        except (IndexError, ValueError):
            await query.message.reply_text("❌ Invalid callback data.")

    # Handle Disable Task callback
    elif data.startswith("disable_"):
        try:
            task_id = int(data.split("_")[1])
            task = await db.get_task(task_id)
            if not task:
                await query.message.reply_text("❌ Task not found.")
                return
            user_id = query.from_user.id
            if task['user_id'] != user_id and user_id not in config.ADMIN_IDS:
                await query.message.reply_text("❌ You don't own this task.")
                return
            
            await db.disable_task(task_id)
            if "edittask" in str(query.message.reply_markup):
                await edittask_menu(update, context)
            else:
                await query.message.reply_text(f"🔴 Task <code>{task_id}</code> disabled!", parse_mode=ParseMode.HTML)
        except (IndexError, ValueError):
            await query.message.reply_text("❌ Invalid callback data.")

    # Handle Delete Task Confirmation
    elif data.startswith("deletetask_confirm_"):
        try:
            task_id = int(data.split("_")[2])
            keyboard = [
                [InlineKeyboardButton("🗑️ Yes, Delete", callback_data=f"deletetask_final_{task_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"edittask_{task_id}")]
            ]
            await query.message.edit_text(
                f"⚠️ <b>Delete Task {task_id}?</b>\n\nAre you sure?",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except (IndexError, ValueError):
             await query.message.reply_text("❌ Error parsing task ID.")

    # Handle Final Delete
    elif data.startswith("deletetask_final_"):
        try:
            task_id = int(data.split("_")[2])
            await db.delete_task(task_id)
            await query.message.edit_text(
                f"✅ Task <code>{task_id}</code> deleted successfully.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 My Tasks", callback_data="mytasks")]])
            )
        except (IndexError, ValueError):
             await query.message.reply_text("❌ Error deleting task.")

    # Handle Cancel
    elif data == "cancel":
        await query.message.edit_text("❌ Operation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END

    # Handle Manage Filters callback
    elif data.startswith("manage_filters_"):
        await manage_filters_menu(update, context) # Call the new handler
        return STATE_MANAGE_FILTERS # Return state managed by manage_filters_menu

    # Handle Edit Task callbacks (e.g., setdelay, setheader, etc.)
    elif data.startswith("edit_"):
        parts = data.split("_")
        if len(parts) < 3: # Expecting "edit_settingtype_taskid"
            await query.message.reply_text("❌ Invalid callback data for editing task.")
            return
            
        setting_type = parts[1] # e.g., "delay", "headerfooter"
        task_id = int(parts[2])
        
        context.user_data['current_task_id'] = task_id # Store for potential use in sub-conversations

        if setting_type == "delay":
            await query.message.reply_text(
                f"Enter the delay in seconds for task <code>{task_id}</code> (between {config.FORWARD_DELAY_MIN} and {config.FORWARD_DELAY_MAX}):",
                parse_mode=ParseMode.HTML
            )
            context.user_data['editing_setting_for_task'] = task_id
            context.user_data['editing_setting_type'] = 'delay'
            # Assuming we'll handle this text input in handle_incoming_message by checking context.user_data
        elif setting_type == "headerfooter":
            keyboard = [
                [InlineKeyboardButton("Set Header", callback_data=f"setheader_prompt_{task_id}")],
                [InlineKeyboardButton("Set Footer", callback_data=f"setfooter_prompt_{task_id}")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"edittask_{task_id}")]
            ]
            await query.message.edit_text(f"Choose to set Header or Footer for task <code>{task_id}</code>:", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
        elif setting_type == "translate":
            langs = ', '.join([f"<code>{k}</code>" for k in config.SUPPORTED_LANGUAGES.keys()])
            await query.message.reply_text(
                f"Enter the language code to translate to for task <code>{task_id}</code>:\n\n"
                f"Supported languages: {langs}\nUse <code>none</code> to disable translation.",
                parse_mode=ParseMode.HTML
            )
            context.user_data['editing_setting_for_task'] = task_id
            context.user_data['editing_setting_type'] = 'translate'
        elif setting_type == "watermark":
            await query.message.reply_text(
                f"Enter watermark text and position for task <code>{task_id}</code> (e.g., `@mybot position`).\n"
                "Positions: bottom-right, bottom-left, top-right, top-left, center\n"
                "Use `none` for the text to remove watermark."
            )
            context.user_data['editing_setting_for_task'] = task_id
            context.user_data['editing_setting_type'] = 'watermark'
        elif setting_type == "schedule":
            await query.message.reply_text(
                f"Enter schedule settings for task <code>{task_id}</code> using the following command format:\n"
                f"<code>/setschedule {task_id} on HH:MM</code> or <code>/setschedule {task_id} off HH:MM</code>.\n\n"
                "Example: `/setschedule 123 on 08:00`"
            )
            # Directing user to use command, not handling via callback directly here.

    # Handle callbacks for filter management (add filter types, modes, remove)
    elif data.startswith("filtertype_"):
        await addfilter_type_callback(update, context) # Use the dedicated callback handler
        return STATE_ADD_FILTER_VALUE # Transition to next state

    elif data.startswith("filtermode_"):
        await addfilter_mode_callback(update, context) # Use the dedicated callback handler
        return ConversationHandler.END # Filter added, end conversation

    elif data.startswith("viewfilters_"):
        await filters_command_callback_handler(update, context) # Call handler to display filters
        return ConversationHandler.END # Exit conversation after displaying filters

    elif data.startswith("removefilter_"):
        await removefilter_callback(update, context) # Call the dedicated remove filter callback handler
        # After removal, it might be good to show the updated list or go back.
        # For now, let's assume it goes back to the main edit task menu if possible.
        # This requires task_id context. If not available, end conversation.
        task_id = context.user_data.get('current_task_id')
        if task_id:
            return STATE_MANAGE_FILTERS # Return to manage filters menu state
        else:
            return ConversationHandler.END


    # Default case: If no specific handler, end conversation or handle gracefully
    return ConversationHandler.END


# Conversation handler for adding filters
add_filter_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(addfilter_start, pattern='^addfilter_(\d+)$')],
    states={
        STATE_ADD_FILTER_TYPE: [CallbackQueryHandler(addfilter_type_callback, pattern='^filtertype_(keyword|regex|user|crypto)$')],
        STATE_ADD_FILTER_VALUE: [MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, addfilter_value_callback)],
        STATE_ADD_FILTER_MODE: [CallbackQueryHandler(addfilter_mode_callback, pattern='^filtermode_(blacklist|whitelist)$')],
        STATE_MANAGE_FILTERS: [CallbackQueryHandler(manage_filters_menu, pattern='^manage_filters_(\d+)$')] # Allow returning to manage filters
    },
    fallbacks=[
        CommandHandler('cancel', lambda u, c: u.message.reply_text("Operation cancelled.") or ConversationHandler.END), # Allow user to cancel
        CallbackQueryHandler(lambda q, c: q.answer() or q.message.reply_text("Operation cancelled.") if q.data.startswith('cancel') else False, pattern='^cancel$'), # Generic cancel callback
        CallbackQueryHandler(lambda q, c: q.answer() or manage_filters_menu(q, c) if q.data.startswith('manage_filters_') else False, pattern='^manage_filters_(\d+)$'), # Back to manage filters menu
        CallbackQueryHandler(lambda q, c: q.answer() or edittask_menu(q, c) if q.data.startswith('edittask_') else False, pattern='^edittask_(\d+)$') # Back to edit task menu
    ],
    # Add persistence if needed for longer conversations
    # persistent=True,
    # name="add_filter_conversation"
)


async def handle_incoming_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages (forwarding logic)"""
    # Determine the message source (private chat message or channel post)
    message = update.message or update.channel_post or update.edited_channel_post
    if not message:
        return

    chat_id = message.chat.id
    # High-visibility log for Render
    print(f"DEBUG: New message from {chat_id} ({message.chat.title or 'Private'})")

    # Check for new task flow (structured via ConversationHandler states)
    if context.user_data.get('awaiting_source'):
        return await handle_source_selection(update, context)
    elif context.user_data.get('awaiting_dest'):
        return await handle_dest_selection(update, context)

    # MAIN FORWARDING LOGIC
    try:
        # Check by numeric ID first
        tasks = await db.get_tasks_by_source(chat_id)
        
        # If not found and it's a channel, try by username
        if not tasks and message.chat.username:
            tasks = await db.get_tasks_by_source(f"@{message.chat.username}")

        if not tasks:
            return

        print(f"DEBUG: Found {len(tasks)} tasks for source {chat_id}")

        for task in tasks:
            if not task.get('is_enabled', 1):
                continue
            
            # Get filters for this task
            filters_list = await db.get_task_filters(task['task_id'])
            
            # Forward via engine
            print(f"DEBUG: Forwarding task {task['task_id']} to {task['destination_chat_id']}")
            success = await forward_engine.forward_message(context.bot, message, task, filters_list)
            
            if success:
                print(f"DEBUG: Successfully forwarded message from {chat_id} to {task['destination_chat_id']}")
            else:
                print(f"DEBUG: Forwarding failed or blocked by filters for task {task['task_id']}")
            
    except Exception as e:
        logger.error(f"Error in handle_incoming_message: {e}", exc_info=True)
        print(f"DEBUG ERROR: {e}")


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
    
    # Task management commands
    application.add_handler(CommandHandler("newtask", newtask))
    application.add_handler(CommandHandler("mytasks", mytasks))
    application.add_handler(CommandHandler("edittask", edittask_menu)) # Command to show edit menu
    application.add_handler(CommandHandler("deletetask", deletetask))
    application.add_handler(CommandHandler("enabletask", enabletask))
    application.add_handler(CommandHandler("disabletask", disabletask))
    
    # Filter management commands (entry points for conversation)
    application.add_handler(CommandHandler("addfilter", addfilter_start)) # Command to start adding a filter
    application.add_handler(CommandHandler("removefilter", removefilter_callback)) # Command to remove a filter by ID
    application.add_handler(CommandHandler("filters", filters_command_handler)) # Command to list filters for a task
    
    # Settings commands
    application.add_handler(CommandHandler("setdelay", setdelay))
    application.add_handler(CommandHandler("setheader", setheader))
    application.add_handler(CommandHandler("setfooter", setfooter))
    application.add_handler(CommandHandler("setwatermark", setwatermark))
    application.add_handler(CommandHandler("settranslate", settranslate))
    application.add_handler(CommandHandler("setschedule", setschedule))
    
    # Content processing commands (placeholders for now, need implementation)
    application.add_handler(CommandHandler("clean", clean))
    application.add_handler(CommandHandler("replace", replace))
    application.add_handler(CommandHandler("removebykeyword", removebykeyword))
    application.add_handler(CommandHandler("removebyline", removebyline))
    
    # Admin commands
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("users", users))
    
    # Callback Query Handlers
    # New task interactive selection handlers
    application.add_handler(CallbackQueryHandler(handle_source_selection, pattern='^select_source_(\d+)$'))
    application.add_handler(CallbackQueryHandler(handle_dest_selection, pattern='^select_dest_(\d+)$'))
    application.add_handler(CallbackQueryHandler(newtask, pattern='^newtask$')) # Handle the newtask button from main menu
    
    # Onboarding guide handlers
    application.add_handler(CallbackQueryHandler(onboarding_guide, pattern='^guide_\d+$'))
    application.add_handler(CallbackQueryHandler(start, pattern='^start_menu$'))
    application.add_handler(CallbackQueryHandler(help_command, pattern='^help_main$'))

    # For callbacks that initiate conversation states
    application.add_handler(CallbackQueryHandler(button_callback, pattern='^(mytasks|enable_.*|filters_.*|edittask_.*|setdelay_.*|headerfooter_.*|translate_.*|watermark_.*|schedule_.*|manage_filters_.*|deletetask_.*|cancel|stats_user)$'))
    # For callbacks handled within ConversationHandler states or specific actions
    application.add_handler(CallbackQueryHandler(filters_command_callback_handler, pattern='^viewfilters_(\d+)$')) # Callback to view filters
    application.add_handler(CallbackQueryHandler(removefilter_callback, pattern='^removefilter_(\d+)$')) # Callback for removing filters
    
    # Add the conversation handler for adding filters
    application.add_handler(add_filter_conv_handler)
    
    # Message handler for forwarding and task creation steps
    application.add_handler(MessageHandler(
        (tg_filters.ALL | tg_filters.ChatType.CHANNEL) & ~tg_filters.COMMAND,
        handle_incoming_message
    ))
    
    # Start the bot
    print("🤖 PLATINUM Forward Bot is starting...")
    print("✅ Bot is running!")
    
    # Run FastAPI server in the background
    config_server = uvicorn.Config(fastapi_app, host="0.0.0.0", port=10000, log_level="info")
    server = uvicorn.Server(config_server)
    asyncio.create_task(server.serve())
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
