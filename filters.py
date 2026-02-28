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
            # Assuming filter_value for user filter is a comma-separated list of user IDs
            try:
                allowed_users = [int(uid.strip()) for uid in f['filter_value'].split(',') if uid.strip()]
            except ValueError:
                print(f"Warning: Could not parse user IDs from filter value: {f['filter_value']}")
                continue # Skip this filter if IDs are invalid
                
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
            keywords = [kw.strip().lower() for kw in f['filter_value'].split(',') if kw.strip()]
            is_whitelist = f['is_whitelist']
            
            if not keywords: # Skip if filter value is empty after split/strip
                continue

            if is_whitelist:
                # Whitelist: message must contain at least one keyword
                if not any(kw in text_lower for kw in keywords):
                    return False
            else:
                # Blacklist: message must NOT contain any keyword
                if any(kw in text_lower for kw in keywords):
                    return False
        
        return True
    
    # ========== REGEX FILTER ==========
    def check_regex_filter(self, text: str, filters: List[Dict]) -> bool:
        """Check if message passes regex filter"""
        regex_filters = [f for f in filters if f['filter_type'] == 'regex']
        if not regex_filters or not text:
            return True
        
        for f in regex_filters:
            try:
                # Use re.search for general pattern matching. 
                # Consider adding flags for case-insensitivity if needed, or handle via regex itself.
                pattern = re.compile(f['filter_value']) 
                matches = pattern.search(text)
                is_whitelist = f['is_whitelist']
                
                if is_whitelist:
                    # Whitelist: message must match the regex pattern
                    if not matches:
                        return False
                else:
                    # Blacklist: message must NOT match the regex pattern
                    if matches:
                        return False
            except re.error as e:
                print(f"Invalid regex pattern: {f['filter_value']} - Error: {e}")
                # For now, we'll skip this filter if invalid to avoid breaking the bot.
                # A more robust solution might notify the user or log this error.
                pass 
        
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
            # Use file_unique_id for photos, videos, documents for better uniqueness
            content = f"photo_{message.photo[-1].file_unique_id}"
        elif message.video:
            content = f"video_{message.video.file_unique_id}"
        elif message.document:
            content = f"doc_{message.document.file_unique_id}"
        elif message.audio:
            content = f"audio_{message.audio.file_unique_id}"
        elif message.voice:
            content = f"voice_{message.voice.file_unique_id}"
        elif message.video_note:
            content = f"video_note_{message.video_note.file_unique_id}"
        elif message.animation:
            content = f"animation_{message.animation.file_unique_id}"
        
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
        
        # Make these options configurable if needed via task settings
        if cleaner_options.get('remove_usernames', True):
            cleaned = re.sub(r'@\w+', '', cleaned)
        
        if cleaner_options.get('remove_urls', True):
            cleaned = re.sub(r'https?://\S+', '', cleaned)
            cleaned = re.sub(r't\.me/\S+', '', cleaned)
        
        if cleaner_options.get('remove_hashtags', True):
            cleaned = re.sub(r'#[\w]+', '', cleaned)
        
        if cleaner_options.get('remove_mentions', True):
            # Basic removal of Markdown links like [text](url)
            cleaned = re.sub(r'\[.*?\]\(.*?\)', '', cleaned)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned) # Replace multiple blank lines with double blank lines
        cleaned = cleaned.strip() # Remove leading/trailing whitespace
        
        return cleaned
    
    # ========== TEXT REPLACEMENT ==========
    def replace_text(self, text: str, replacements: List[Dict]) -> str:
        """Replace text based on replacement rules.
        
        Replacements should be a list of dicts, e.g.:
        [{'old': 'text_to_find', 'new': 'replacement_text', 'case_sensitive': True}, ...]
        """
        if not text or not replacements:
            return text
        
        result = text
        for rep in replacements:
            old_text = rep.get('old')
            new_text = rep.get('new', '') # Default to empty string if not provided
            case_sensitive = rep.get('case_sensitive', True)
            
            if not old_text: # Skip if 'old' text is missing
                continue
                
            if case_sensitive:
                result = result.replace(old_text, new_text)
            else:
                # Case insensitive replacement using regex
                # re.escape ensures special characters in old_text are treated literally
                pattern = re.compile(re.escape(old_text), re.IGNORECASE)
                result = pattern.sub(new_text, result)
        
        return result
    
    # ========== REMOVE LINE BY KEYWORD ==========
    def remove_line_by_keyword(self, text: str, keywords: List[str]) -> str:
        """Remove lines containing specific keywords"""
        if not text or not keywords:
            return text
        
        lines = text.split('\n')
        filtered_lines = []
        
        # Normalize keywords to lower case for case-insensitive matching
        keywords_lower = [kw.lower() for kw in keywords if kw.strip()]
        
        if not keywords_lower: # Skip if keywords list is empty after stripping
            return text

        for line in lines:
            line_lower = line.lower()
            # Check if any of the keywords are present in the line
            if not any(kw in line_lower for kw in keywords_lower):
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    # ========== REMOVE LINE BY ORDER ==========
    def remove_line_by_order(self, text: str, line_numbers: List[int]) -> str:
        """Remove lines by their order (1-indexed)"""
        if not text or not line_numbers:
            return text
        
        lines = text.split('\n')
        filtered_lines = []
        
        # Ensure line_numbers are sorted and unique for efficiency if needed, but not strictly required for correctness
        valid_line_numbers = set(ln for ln in line_numbers if isinstance(ln, int) and ln > 0)

        for i, line in enumerate(lines, 1):
            if i not in valid_line_numbers:
                filtered_lines.append(line)
        
        return '\n'.join(filtered_lines)
    
    # ========== TRANSLATION ==========
    async def translate_text(self, text: str, target_lang: str) -> str:
        """Translate text to target language"""
        if not text or not target_lang or target_lang not in config.SUPPORTED_LANGUAGES:
            return text
        
        try:
            result = self.translator.translate(text, dest=target_lang)
            return result.text
        except Exception as e:
            # Log the error or handle it more gracefully
            print(f"Translation error: {e}")
            return text # Return original text if translation fails
    
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
        # Ensure text is not None before concatenation
        result = text if text is not None else ""
        
        if header:
            result = f"{header}\n\n{result}"
        
        if footer:
            result = f"{result}\n\n{footer}"
        
        return result
    
    # ========== APPLY ALL FILTERS ==========
    async def apply_filters(self, message, task: Dict, filters: List[Dict], db) -> Optional[Dict]:
        """Apply all filters and return processed message data"""
        # Default text and caption from message.text or message.caption
        initial_text = message.text if message.text else message.caption
        processed_caption = message.caption # Keep original caption if text is empty
        
        result = {
            'should_forward': True,
            'text': initial_text or "", # Ensure text is at least an empty string
            'caption': processed_caption,
            'media': None, # Placeholder for media handling if needed
            'reply_markup': message.reply_markup # Preserve reply markup if any
        }
        
        # Check user filter
        if not self.check_user_filter(message, filters):
            result['should_forward'] = False
            return result
        
        # Check keyword filter
        if not self.check_keyword_filter(result['text'], filters):
            result['should_forward'] = False
            return result
        
        # Check regex filter
        if not self.check_regex_filter(result['text'], filters):
            result['should_forward'] = False
            return result
        
        # Check crypto filter
        if not self.check_crypto_filter(result['text'], filters):
            result['should_forward'] = False
            return result
        
        # Check duplicate filter
        if task.get('remove_duplicates', 1): # Default to true if not specified
            if await self.check_duplicate(task['task_id'], message, db):
                result['should_forward'] = False
                return result
        
        # Apply cleaner filter - options should ideally come from task settings
        cleaner_options = {
            'remove_usernames': True,
            'remove_urls': True,
            'remove_hashtags': True,
            'remove_mentions': True
        }
        result['text'] = self.apply_cleaner(result['text'], cleaner_options)
        
        # Convert buttons to text if enabled
        if task.get('convert_buttons', 0): # Default to false if not specified
            button_text = self.convert_buttons_to_text(message)
            if button_text:
                # Append button text to the main message text
                result['text'] += f"\n\n{button_text}"
        
        # Add header/footer
        # Ensure header_text and footer_text are retrieved safely from task dict
        header_text = task.get('header_text')
        footer_text = task.get('footer_text')

        if header_text:
            result['text'] = self.add_header_footer(result['text'], header=header_text)
        
        if footer_text:
            result['text'] = self.add_header_footer(result['text'], footer=footer_text)
        
        # Translate if enabled
        # Ensure translate_to is retrieved safely and is not None/empty
        target_lang = task.get('translate_to')
        if target_lang:
            result['text'] = await self.translate_text(result['text'], target_lang)
        
        return result

# Global filters instance
filters = MessageFilters()