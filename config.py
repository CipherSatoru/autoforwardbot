"""
Telegram Forward Bot - PLATINUM Edition
Configuration File
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '123456789').split(',')))

# Userbot (Telethon) Configuration
# Get these from https://my.telegram.org
API_ID = os.getenv('API_ID', 'YOUR_API_ID')
API_HASH = os.getenv('API_HASH', 'YOUR_API_HASH')

# Database
DATABASE_FILE = 'forward_bot.db'

# Forwarding Settings
MAX_FORWARD_TASKS = 10000  # Unlimited for premium
FORWARD_DELAY_MIN = 1  # Minimum delay in seconds
FORWARD_DELAY_MAX = 3600  # Maximum delay in seconds

# File Settings
MAX_FILE_SIZE_MB = 2000  # 2GB (Telegram limit)
SUPPORTED_MEDIA_TYPES = ['photo', 'video', 'audio', 'document', 'voice', 'video_note', 'sticker']

# Translation Settings
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh': 'Chinese',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'tr': 'Turkish',
    'pl': 'Polish',
    'nl': 'Dutch',
    'id': 'Indonesian',
    'vi': 'Vietnamese',
    'th': 'Thai',
    'fa': 'Persian',
    'ur': 'Urdu'
}

# Crypto Keywords (for crypto filter)
CRYPTO_KEYWORDS = [
    'btc', 'bitcoin', 'eth', 'ethereum', 'crypto', 'cryptocurrency',
    'blockchain', 'wallet', 'binance', 'coinbase', 'trading', 'signal',
    'pump', 'dump', 'moon', 'token', 'nft', 'defi', 'airdrop'
]

# Scheduler Settings
SCHEDULER_TIMEZONE = 'UTC'

# Watermark Settings
DEFAULT_WATERMARK_TEXT = "@ForwardedByBot"
WATERMARK_POSITIONS = ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center']

# Cleaner Filter Patterns
CLEANER_PATTERNS = [
    r'@\w+',  # Remove usernames
    r'https?://\S+',  # Remove URLs
    r't\.me/\S+',  # Remove Telegram links
    r'#[\w]+',  # Remove hashtags
]

# Messages
WELCOME_MESSAGE = """
🤖 <b>Welcome to PLATINUM Forward Bot!</b>

I am the most advanced message forwarding bot on Telegram with unlimited features!

<b>Key Features:</b>
✅ Unlimited Forward Tasks
✅ Advanced Filters (User, Keyword, Crypto, Duplicate)
✅ Translation Support (20+ Languages)
✅ Watermark & Header/Footer
✅ Auto Scheduling
✅ Topic Support
✅ And much more!

Use /help to see all commands.
"""

HELP_MESSAGE = """
📖 <b>PLATINUM Forward Bot - Commands</b>

<b>🔄 Forward Management:</b>
/newtask - Create a new forward task
/mytasks - List all your forward tasks
/edittask - Edit an existing task
/deletetask - Delete a forward task
/enabletask - Enable a task
/disabletask - Disable a task
/clone - Clone a source chat

<b>🛠️ Filters:</b>
/addfilter - Add filter to task
/removefilter - Remove filter
/filters - View active filters

<b>⚙️ Settings:</b>
/setdelay - Set forwarding delay
/setschedule - Schedule power on/off
/setheader - Add header to messages
/setfooter - Add footer to messages
/setwatermark - Add watermark to media
/settranslate - Enable translation

<b>🧹 Content Processing:</b>
/clean - Clean message (remove links, usernames)
/replace - Replace text in messages
/removebykeyword - Remove lines by keyword
/removebyline - Remove lines by line number

<b>📊 Admin:</b>
/stats - View bot statistics
/broadcast - Broadcast message to all users
/users - List all users
"""
