"""
Telegram Forward Bot - Advanced Filters Module
"""
import re
import hashlib
from typing import List, Dict, Optional
from googletrans import Translator
import config

class MessageFilters:
    def __init__(self):
        self.translator = Translator()
    
    # ========== USER FILTER ==========
    def check_user_filter(self, message, filters: List[Dict]) -> bool:
        """Check if message passes user filter"""
        user_filters = [f for f in filters if f['filter_type'] == 'user']
        if not user_filters:
            return True
        
        sender_id = message.from_user.id if message.from_user else None
        
        for f in user_filters:
            allowed_users = [int(uid.strip()) for uid in f['filter_value'].split(',')]
            is_whitelist = f['is_whitelist']
            
            if is_whitelist:
                # Whitelist: only allow these users
                if sender_id not in allowed_users:
                    return False
            else:
                # Blacklist: block these users
                if sender_id in allowed_users:
                    return False
        
        return True
    
    # ========== KEYWORD FILTER ==========
    def check_keyword_filter(self, text: str, filters: List[Dict]) -> bool:
        """Check if message passes keyword filter"""
        keyword_filters = [f for f in filters if f['filter_type'] == 'keyword']
        if not keyword_filters or not text:
            return True
        
        text_lower = text.lower()
        
        for f in keyword_filters:
            keywords = [kw.strip().lower() for kw in f['filter_value'].split(',')]
            is_whitelist = f['is_whitelist']
            
            if is_whitelist:
                # Whitelist: message must contain at least one keyword
                if not any(kw in text_lower for kw in keywords):
                    return False
            else:
                # Blacklist: message must NOT contain any keyword
                if any(kw in text_lower for kw in keywords):
                    return False
        
        return True
    
    # ========== CRYPTO FILTER ==========
    def check_crypto_filter(self, text: str, filters: List[Dict], allow_crypto: bool = True) -> bool:
        """Filter messages based on crypto content"""
        crypto_filters = [f for f in filters if f['filter_type'] == 'crypto']
        if not crypto_filters or not text:
            return True
        
        text_lower = text.lower()
        has_crypto = any(kw in text_lower for kw in config.CRYPTO_KEYWORDS)
        
        for f in crypto_filters:
            filter_action = f['filter_value'].lower()
            
            if filter_action == 'only_crypto':
                return has_crypto
            elif filter_action == 'no_crypto':
                return not has_crypto
        
        return True
    
    # ========== DUPLICATE FILTER ==========
    async def check_duplicate(self, task_id: int, message, db) -> bool:
        """Check if message is a duplicate"""
        # Create hash from message content
        content = ""
        if message.text:
            content = message.text
        elif message.caption:
            content = message.caption
        elif message.photo:
            content = f"photo_{message.photo[-1].file_unique_id}"
        elif message.video:
            content = f"video_{message.video.file_unique_id}"
        elif message.document:
            content = f"doc_{message.document.file_unique_id}"
        
        if not content:
            return False
        
        message_hash = hashlib.md5(content.encode()).hexdigest()
        return await db.is_duplicate(task_id, message_hash)
    
    # ========== CLEANER FILTER ==========
    def apply_cleaner(self, text: str, cleaner_options: Dict) -> str:
        """Clean message by removing specified patterns"""
        if not text:
            return text
        
        cleaned = text
        
        if cleaner_options.get('remove_usernames', True):
            cleaned = re.sub(r'@\w+', '', cleaned)
        
        if cleaner_options.get('remove_urls', True):
            cleaned = re.sub(r'https?://\S+', '', cleaned)
            cleaned = re.sub(r't\.me/\S+', '', cleaned)
        
        if cleaner_options.get('remove_hashtags', True):
            cleaned = re.sub(r'#[\w]+', '', cleaned)
        
        if cleaner_options.get('remove_mentions', True):
            cleaned = re.sub(r'\[.*?\]\(.*?\)', '', cleaned)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    # ========== TEXT REPLACEMENT ==========
    def replace_text(self, text: str, replacements: List[Dict]) -> str:
        """Replace text based on replacement rules"""
        if not text:
            return text
        
        result = text
        for rep in replacements:
            old_text = rep.get('old', '')
            new_text = rep.get('new', '')
            case_sensitive = rep.get('case_sensitive', True)
            
            if case_sensitive:
                result = result.replace(old_text, new_text)
            else:
                # Case insensitive replacement
                pattern = re.compile(re.escape(old_text), re.IGNORECASE)
                result = pattern.sub(new_text, result)
        
        return result
    
    # ========== REMOVE LINE BY KEYWORD ==========
    def remove_line_by_keyword(self, text: str, keywords: List[str]) -> str:
        """Remove lines containing specific keywords"""
        if not text:
            return text
        
        lines = text.split('\n')
        filtered_lines = []
        
        for line in lines:
            line_lower = line.lower()
            if not any(kw.lower() in line_lower for kw in keywords):
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    # ========== REMOVE LINE BY ORDER ==========
    def remove_line_by_order(self, text: str, line_numbers: List[int]) -> str:
        """Remove lines by their order (1-indexed)"""
        if not text:
            return text
        
        lines = text.split('\n')
        filtered_lines = []
        
        for i, line in enumerate(lines, 1):
            if i not in line_numbers:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    # ========== TRANSLATION ==========
    async def translate_text(self, text: str, target_lang: str) -> str:
        """Translate text to target language"""
        if not text or target_lang not in config.SUPPORTED_LANGUAGES:
            return text
        
        try:
            result = self.translator.translate(text, dest=target_lang)
            return result.text
        except Exception as e:
            print(f"Translation error: {e}")
            return text
    
    # ========== CONVERT BUTTONS TO TEXT ==========
    def convert_buttons_to_text(self, message) -> str:
        """Extract button text from inline keyboard"""
        if not message.reply_markup or not message.reply_markup.inline_keyboard:
            return ""
        
        button_texts = []
        for row in message.reply_markup.inline_keyboard:
            for button in row:
                if button.text:
                    button_texts.append(f"• {button.text}")
        
        return '\n'.join(button_texts)
    
    # ========== ADD HEADER/FOOTER ==========
    def add_header_footer(self, text: str, header: str = None, footer: str = None) -> str:
        """Add header and/or footer to message"""
        result = text or ""
        
        if header:
            result = f"{header}\n\n{result}"
        
        if footer:
            result = f"{result}\n\n{footer}"
        
        return result
    
    # ========== APPLY ALL FILTERS ==========
    async def apply_filters(self, message, task: Dict, filters: List[Dict], db) -> Optional[Dict]:
        """Apply all filters and return processed message data"""
        result = {
            'should_forward': True,
            'text': message.text or message.caption or "",
            'caption': message.caption,
            'media': None,
            'reply_markup': None
        }
        
        # Check user filter
        if not self.check_user_filter(message, filters):
            result['should_forward'] = False
            return result
        
        # Check keyword filter
        if not self.check_keyword_filter(result['text'], filters):
            result['should_forward'] = False
            return result
        
        # Check crypto filter
        if not self.check_crypto_filter(result['text'], filters):
            result['should_forward'] = False
            return result
        
        # Check duplicate filter
        if task.get('remove_duplicates', 1):
            if await self.check_duplicate(task['task_id'], message, db):
                result['should_forward'] = False
                return result
        
        # Apply cleaner filter
        cleaner_options = {
            'remove_usernames': True,
            'remove_urls': True,
            'remove_hashtags': True,
            'remove_mentions': True
        }
        result['text'] = self.apply_cleaner(result['text'], cleaner_options)
        
        # Convert buttons to text if enabled
        if task.get('convert_buttons', 0):
            button_text = self.convert_buttons_to_text(message)
            if button_text:
                result['text'] += f"\n\n{button_text}"
        
        # Add header/footer
        if task.get('header_text'):
            result['text'] = self.add_header_footer(result['text'], header=task['header_text'])
        
        if task.get('footer_text'):
            result['text'] = self.add_header_footer(result['text'], footer=task['footer_text'])
        
        # Translate if enabled
        if task.get('translate_to'):
            result['text'] = await self.translate_text(result['text'], task['translate_to'])
        
        return result

# Global filters instance
filters = MessageFilters()
