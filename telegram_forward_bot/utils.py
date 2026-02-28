"""
Telegram Forward Bot - Utility Functions
"""
import re
from typing import List, Dict
import config

def format_chat_name(chat_id: int, title: str = None) -> str:
    """Format chat name for display"""
    if title:
        return f"{title} ({chat_id})"
    return str(chat_id)

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to maximum length"""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def parse_time_string(time_str: str) -> tuple:
    """Parse time string (HH:MM) to hours and minutes"""
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            return None
        hour = int(parts[0])
        minute = int(parts[1])
        if 0 <= hour < 24 and 0 <= minute < 60:
            return (hour, minute)
        return None
    except:
        return None

def format_duration(seconds: int) -> str:
    """Format seconds to human-readable duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def is_valid_chat_id(chat_id) -> bool:
    """Check if chat ID is valid"""
    try:
        # Bot API chat IDs can be integers or strings (for usernames)
        if isinstance(chat_id, int):
            return True
        if isinstance(chat_id, str):
            # Check if it's a username (starts with @) or numeric string
            if chat_id.startswith('@'):
                return len(chat_id) > 1
            return chat_id.lstrip('-').isdigit()
        return False
    except:
        return False

def extract_urls(text: str) -> List[str]:
    """Extract URLs from text"""
    if not text:
        return []
    
    url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    return re.findall(url_pattern, text)

def extract_usernames(text: str) -> List[str]:
    """Extract Telegram usernames from text"""
    if not text:
        return []
    
    username_pattern = r'@(\w{5,32})'
    return re.findall(username_pattern, text)

def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text"""
    if not text:
        return []
    
    hashtag_pattern = r'#(\w+)'
    return re.findall(hashtag_pattern, text)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def format_number(num: int) -> str:
    """Format large numbers with K/M suffix"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    return str(num)

def get_media_type(message) -> str:
    """Get the media type of a message"""
    if message.text:
        return "text"
    elif message.photo:
        return "photo"
    elif message.video:
        return "video"
    elif message.audio:
        return "audio"
    elif message.voice:
        return "voice"
    elif message.video_note:
        return "video_note"
    elif message.document:
        return "document"
    elif message.sticker:
        return "sticker"
    elif message.animation:
        return "animation"
    elif message.poll:
        return "poll"
    elif message.location:
        return "location"
    elif message.contact:
        return "contact"
    return "unknown"

def get_file_size(message) -> int:
    """Get file size in bytes from message"""
    if message.photo:
        return message.photo[-1].file_size or 0
    elif message.video:
        return message.video.file_size or 0
    elif message.audio:
        return message.audio.file_size or 0
    elif message.voice:
        return message.voice.file_size or 0
    elif message.video_note:
        return message.video_note.file_size or 0
    elif message.document:
        return message.document.file_size or 0
    elif message.sticker:
        return message.sticker.file_size or 0
    elif message.animation:
        return message.animation.file_size or 0
    return 0

def format_file_size(size_bytes: int) -> str:
    """Format file size to human-readable string"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def create_progress_bar(current: int, total: int, length: int = 20) -> str:
    """Create a text progress bar"""
    if total == 0:
        return "[" + " " * length + "] 0%"
    
    filled = int(length * current / total)
    bar = "█" * filled + "░" * (length - filled)
    percent = int(100 * current / total)
    
    return f"[{bar}] {percent}%"

def escape_markdown(text: str) -> str:
    """Escape Markdown special characters"""
    if not text:
        return ""
    
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def contains_crypto_keywords(text: str) -> bool:
    """Check if text contains crypto-related keywords"""
    if not text:
        return False
    
    text_lower = text.lower()
    return any(kw in text_lower for kw in config.CRYPTO_KEYWORDS)

def is_spam_text(text: str) -> bool:
    """Basic spam detection"""
    if not text:
        return False
    
    spam_indicators = [
        text.count('!') > 5,
        text.count('?') > 5,
        text.count('$') > 3,
        len(re.findall(r'\b[A-Z]{5,}\b', text)) > 3,
        'click here' in text.lower(),
        'limited time' in text.lower(),
        'act now' in text.lower(),
    ]
    
    return sum(spam_indicators) >= 3
