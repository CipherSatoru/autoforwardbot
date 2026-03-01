"""
Telegram Forward Bot - Core Forwarder Module
"""
import asyncio
import hashlib
from typing import Optional, Dict
from telegram import Update, Bot
from telegram.constants import ParseMode
import config
from database import db
from filters import filters
from watermark import watermark_processor

class ForwardEngine:
    def __init__(self):
        self.processing_messages = set()  # Track messages being processed
    
    async def forward_message(self, bot: Bot, message, task: Dict, 
                             filters_list: list) -> bool:
        """Forward a single message with all processing"""
        task_id = task['task_id']
        dest_chat_id = task['destination_chat_id']
        
        # Check if already processing (prevent duplicates)
        msg_key = f"{task_id}_{message.message_id}"
        if msg_key in self.processing_messages:
            return False
        
        self.processing_messages.add(msg_key)
        
        try:
            # Apply filters
            filter_result = await filters.apply_filters(message, task, filters_list, db)
            
            if not filter_result['should_forward']:
                return False
            
            # Apply delay if set
            delay = task.get('forward_delay', 0)
            if delay > 0:
                await asyncio.sleep(delay)
            
            # Process and forward message
            forwarded = await self._send_processed_message(
                bot, message, dest_chat_id, filter_result, task
            )
            
            if forwarded:
                # Record for duplicate detection
                content = filter_result['text'] or ""
                message_hash = hashlib.md5(content.encode()).hexdigest()
                await db.add_forwarded_message(
                    task_id, message.message_id, 
                    message.chat.id, message_hash
                )
                
                # Update statistics
                await db.increment_stat(task['user_id'], task_id)
                
                return True
            
        except Exception as e:
            print(f"Forward error: {e}")
        finally:
            self.processing_messages.discard(msg_key)
        
        return False
    
    async def _send_processed_message(self, bot: Bot, message, dest_chat_id: int,
                                     filter_result: Dict, task: Dict) -> bool:
        """Send the processed message to destination"""
        try:
            processed_text = filter_result['text']
            has_watermark = bool(task.get('watermark_text') and task.get('watermark_text') != 'none')
            
            # If we need to watermark, we must use the manual download/upload method
            if has_watermark and (message.photo or message.video):
                 # Fallthrough to existing manual logic for watermarking
                 pass
            
            # For other cases, try to use copy_message which preserves everything perfectly
            # unless we have completely changed the text/caption beyond simple addition
            elif not has_watermark:
                try:
                    # If we have a processed text (header/footer/translation), we use it as caption/text
                    # copy_message takes 'caption' for media or 'text' is implied for text messages?
                    # Actually copy_message has 'caption' parameter which overrides original caption.
                    # For text messages, we can't use copy_message if we want to change the text.
                    # But for media, we can use copy_message and replace the caption.
                    
                    if message.text:
                        # For text, if we changed it (cleaner/header/footer), we must use send_message
                        # Check if text was modified? filter_result['text'] is the modified text.
                        # Always use send_message for text to ensure our modifications apply.
                        await bot.send_message(
                            chat_id=dest_chat_id,
                            text=processed_text,
                            parse_mode=ParseMode.HTML if self._has_html(processed_text) else None,
                            disable_web_page_preview=True
                        )
                        return True
                    
                    else:
                        # For media (photo, video, etc), use copy_message with new caption
                        await bot.copy_message(
                            chat_id=dest_chat_id,
                            from_chat_id=message.chat.id,
                            message_id=message.message_id,
                            caption=processed_text,
                            parse_mode=ParseMode.HTML if self._has_html(processed_text) else None
                        )
                        return True
                        
                except Exception as e:
                    # Fallback to manual method if copy_message fails (e.g. some restriction?)
                    # print(f"copy_message failed, falling back: {e}")
                    pass

            # Manual handling (Watermarking or Fallback)
            if message.text:
                # Already handled above, but just in case
                await bot.send_message(
                    chat_id=dest_chat_id,
                    text=processed_text,
                    parse_mode=ParseMode.HTML if self._has_html(processed_text) else None,
                    disable_web_page_preview=True
                )
                return True
            
            elif message.photo:
                # Photo with optional watermark
                photo = message.photo[-1]  # Get highest resolution
                
                if task.get('watermark_text'):
                    # Download and add watermark
                    watermarked = await watermark_processor.process_photo_with_watermark(
                        bot, photo.file_id, 
                        task['watermark_text'],
                        task.get('watermark_position', 'bottom-right')
                    )
                    
                    if watermarked:
                        await bot.send_photo(
                            chat_id=dest_chat_id,
                            photo=watermarked,
                            caption=processed_text,
                            parse_mode=ParseMode.HTML if self._has_html(processed_text) else None
                        )
                        return True
                
                # Forward without watermark or if watermark failed
                await bot.send_photo(
                    chat_id=dest_chat_id,
                    photo=photo.file_id,
                    caption=processed_text,
                    parse_mode=ParseMode.HTML if self._has_html(processed_text) else None
                )
                return True
            
            elif message.video:
                # Video
                await bot.send_video(
                    chat_id=dest_chat_id,
                    video=message.video.file_id,
                    caption=processed_text,
                    parse_mode=ParseMode.HTML if self._has_html(processed_text) else None
                )
                return True
            
            elif message.audio:
                # Audio
                await bot.send_audio(
                    chat_id=dest_chat_id,
                    audio=message.audio.file_id,
                    caption=processed_text,
                    parse_mode=ParseMode.HTML if self._has_html(processed_text) else None
                )
                return True
            
            elif message.voice:
                # Voice message
                await bot.send_voice(
                    chat_id=dest_chat_id,
                    voice=message.voice.file_id,
                    caption=processed_text
                )
                return True
            
            elif message.video_note:
                # Video note (round video)
                await bot.send_video_note(
                    chat_id=dest_chat_id,
                    video_note=message.video_note.file_id
                )
                return True
            
            elif message.document:
                # Document
                await bot.send_document(
                    chat_id=dest_chat_id,
                    document=message.document.file_id,
                    caption=processed_text,
                    parse_mode=ParseMode.HTML if self._has_html(processed_text) else None
                )
                return True
            
            elif message.sticker:
                # Sticker
                await bot.send_sticker(
                    chat_id=dest_chat_id,
                    sticker=message.sticker.file_id
                )
                return True
            
            elif message.animation:
                # Animation (GIF)
                await bot.send_animation(
                    chat_id=dest_chat_id,
                    animation=message.animation.file_id,
                    caption=processed_text
                )
                return True
            
            elif message.poll:
                # Poll - can't forward directly, send as text
                poll = message.poll
                poll_text = f"📊 <b>Poll:</b> {poll.question}\n\n"
                for i, option in enumerate(poll.options, 1):
                    poll_text += f"{i}. {option.text}\n"
                
                await bot.send_message(
                    chat_id=dest_chat_id,
                    text=poll_text,
                    parse_mode=ParseMode.HTML
                )
                return True
            
            elif message.location:
                # Location
                await bot.send_location(
                    chat_id=dest_chat_id,
                    latitude=message.location.latitude,
                    longitude=message.location.longitude
                )
                return True
            
            elif message.contact:
                # Contact
                contact = message.contact
                await bot.send_contact(
                    chat_id=dest_chat_id,
                    phone_number=contact.phone_number,
                    first_name=contact.first_name,
                    last_name=contact.last_name
                )
                return True
            
            return False
            
        except Exception as e:
            print(f"Send processed message error: {e}")
            return False
    
    def _has_html(self, text: str) -> bool:
        """Check if text contains HTML tags"""
        if not text:
            return False
        html_tags = ['<b>', '</b>', '<i>', '</i>', '<code>', '</code>', 
                     '<pre>', '</pre>', '<a ', '</a>', '<u>', '</u>',
                     '<s>', '</s>', '<tg-spoiler>', '</tg-spoiler>']
        return any(tag in text for tag in html_tags)
    
    async def clone_source_chat(self, bot: Bot, task: Dict, limit: int = 100):
        """Clone messages from source chat to destination"""
        try:
            source_chat_id = task['source_chat_id']
            dest_chat_id = task['destination_chat_id']
            
            # Get recent messages from source
            messages = []
            offset_id = 0
            
            while len(messages) < limit:
                try:
                    # Note: This requires userbot (Telethon/Pyrogram) to access history
                    # Bot API cannot get chat history directly
                    # For now, we'll document this limitation
                    break
                except:
                    break
            
            return len(messages)
            
        except Exception as e:
            print(f"Clone error: {e}")
            return 0
    
    async def broadcast_message(self, bot: Bot, message_text: str, 
                               user_ids: list, parse_mode: str = None):
        """Broadcast message to multiple users"""
        sent_count = 0
        failed_count = 0
        
        for user_id in user_ids:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode=parse_mode
                )
                sent_count += 1
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                print(f"Broadcast to {user_id} failed: {e}")
                failed_count += 1
        
        return sent_count, failed_count

# Global forward engine
forward_engine = ForwardEngine()
