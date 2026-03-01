"""
Telegram Forward Bot - Database Module
"""
import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import config

class Database:
    def __init__(self, db_file: str = config.DATABASE_FILE):
        self.db_file = db_file
    
    async def init(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_file) as db:
            # Users table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    joined_date TEXT,
                    is_premium INTEGER DEFAULT 1,
                    is_banned INTEGER DEFAULT 0
                )
            ''')
            
            # Forward tasks table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS forward_tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    source_chat_id INTEGER,
                    source_chat_title TEXT,
                    destination_chat_id INTEGER,
                    destination_chat_title TEXT,
                    is_enabled INTEGER DEFAULT 1,
                    created_date TEXT,
                    forward_delay INTEGER DEFAULT 0,
                    header_text TEXT,
                    footer_text TEXT,
                    translate_to TEXT,
                    watermark_text TEXT,
                    watermark_position TEXT DEFAULT 'bottom-right',
                    power_on_time TEXT,
                    power_off_time TEXT,
                    remove_duplicates INTEGER DEFAULT 1,
                    convert_buttons INTEGER DEFAULT 0,
                    clone_source INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Filters table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS filters (
                    filter_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    filter_type TEXT,
                    filter_value TEXT,
                    is_whitelist INTEGER DEFAULT 0,
                    FOREIGN KEY (task_id) REFERENCES forward_tasks(task_id) ON DELETE CASCADE
                )
            ''')
            
            # Forwarded messages (for duplicate detection)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS forwarded_messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    original_message_id INTEGER,
                    source_chat_id INTEGER,
                    message_hash TEXT,
                    forwarded_date TEXT,
                    FOREIGN KEY (task_id) REFERENCES forward_tasks(task_id) ON DELETE CASCADE
                )
            ''')
            
            # Scheduled posts table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_posts (
                    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER,
                    chat_id INTEGER,
                    message_content TEXT,
                    schedule_time TEXT,
                    is_recurring INTEGER DEFAULT 0,
                    recurrence_pattern TEXT,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (task_id) REFERENCES forward_tasks(task_id) ON DELETE CASCADE
                )
            ''')
            
            # Statistics table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS statistics (
                    stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    task_id INTEGER,
                    messages_forwarded INTEGER DEFAULT 0,
                    last_forward_date TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (task_id) REFERENCES forward_tasks(task_id) ON DELETE CASCADE
                )
            ''')
            
            await db.commit()
    
    # User operations
    async def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, joined_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, datetime.now().isoformat()))
            await db.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def get_all_users(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM users WHERE is_banned = 0') as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def ban_user(self, user_id: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
            await db.commit()
    
    # Forward task operations
    async def create_task(self, user_id: int, source_chat_id: int, source_chat_title: str,
                         destination_chat_id: int, destination_chat_title: str) -> int:
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute('''
                INSERT INTO forward_tasks (user_id, source_chat_id, source_chat_title,
                                         destination_chat_id, destination_chat_title, created_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, source_chat_id, source_chat_title, destination_chat_id, 
                  destination_chat_title, datetime.now().isoformat()))
            await db.commit()
            return cursor.lastrowid
    
    async def get_task(self, task_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM forward_tasks WHERE task_id = ?', (task_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def get_user_tasks(self, user_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT * FROM forward_tasks WHERE user_id = ? ORDER BY created_date DESC
            ''', (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_all_active_tasks(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('''
                SELECT * FROM forward_tasks WHERE is_enabled = 1
            ''') as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_tasks_by_source(self, source_chat_id: int) -> List[Dict]:
        """Get all active tasks for a specific source chat ID"""
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            # We use CAST(source_chat_id AS TEXT) if it's stored as text, 
            # but schema says INTEGER. Let's try matching both or use simple match.
            async with db.execute('''
                SELECT * FROM forward_tasks WHERE source_chat_id = ? AND is_enabled = 1
            ''', (source_chat_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def update_task(self, task_id: int, **kwargs):
        async with aiosqlite.connect(self.db_file) as db:
            for key, value in kwargs.items():
                await db.execute(f'UPDATE forward_tasks SET {key} = ? WHERE task_id = ?', (value, task_id))
            await db.commit()
    
    async def delete_task(self, task_id: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('DELETE FROM forward_tasks WHERE task_id = ?', (task_id,))
            await db.commit()
    
    async def enable_task(self, task_id: int):
        await self.update_task(task_id, is_enabled=1)
    
    async def disable_task(self, task_id: int):
        await self.update_task(task_id, is_enabled=0)
    
    # Filter operations
    async def add_filter(self, task_id: int, filter_type: str, filter_value: str, is_whitelist: bool = False):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('''
                INSERT INTO filters (task_id, filter_type, filter_value, is_whitelist)
                VALUES (?, ?, ?, ?)
            ''', (task_id, filter_type, filter_value, int(is_whitelist)))
            await db.commit()
    
    async def get_task_filters(self, task_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM filters WHERE task_id = ?', (task_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def delete_filter(self, filter_id: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('DELETE FROM filters WHERE filter_id = ?', (filter_id,))
            await db.commit()
    
    # Duplicate detection
    async def is_duplicate(self, task_id: int, message_hash: str) -> bool:
        async with aiosqlite.connect(self.db_file) as db:
            async with db.execute('''
                SELECT 1 FROM forwarded_messages 
                WHERE task_id = ? AND message_hash = ?
            ''', (task_id, message_hash)) as cursor:
                return await cursor.fetchone() is not None
    
    async def add_forwarded_message(self, task_id: int, original_message_id: int, 
                                    source_chat_id: int, message_hash: str):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('''
                INSERT INTO forwarded_messages (task_id, original_message_id, source_chat_id, message_hash, forwarded_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (task_id, original_message_id, source_chat_id, message_hash, datetime.now().isoformat()))
            await db.commit()
    
    # Statistics
    async def increment_stat(self, user_id: int, task_id: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('''
                INSERT INTO statistics (user_id, task_id, messages_forwarded, last_forward_date)
                VALUES (?, ?, 1, ?)
                ON CONFLICT DO UPDATE SET 
                    messages_forwarded = messages_forwarded + 1,
                    last_forward_date = ?
            ''', (user_id, task_id, datetime.now().isoformat(), datetime.now().isoformat()))
            await db.commit()
    
    async def get_stats(self, user_id: int = None) -> Dict:
        async with aiosqlite.connect(self.db_file) as db:
            if user_id:
                async with db.execute('''
                    SELECT SUM(messages_forwarded) FROM statistics WHERE user_id = ?
                ''', (user_id,)) as cursor:
                    result = await cursor.fetchone()
                    return {'total_forwarded': result[0] or 0}
            else:
                async with db.execute('''
                    SELECT COUNT(DISTINCT user_id), COUNT(DISTINCT task_id), SUM(messages_forwarded)
                    FROM statistics
                ''') as cursor:
                    result = await cursor.fetchone()
                    return {
                        'total_users': result[0] or 0,
                        'total_tasks': result[1] or 0,
                        'total_forwarded': result[2] or 0
                    }
    
    # Scheduled posts
    async def add_scheduled_post(self, task_id: int, chat_id: int, message_content: str,
                                 schedule_time: str, is_recurring: bool = False, 
                                 recurrence_pattern: str = None) -> int:
        async with aiosqlite.connect(self.db_file) as db:
            cursor = await db.execute('''
                INSERT INTO scheduled_posts (task_id, chat_id, message_content, schedule_time, 
                                            is_recurring, recurrence_pattern, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', (task_id, chat_id, message_content, schedule_time, int(is_recurring), recurrence_pattern))
            await db.commit()
            return cursor.lastrowid
    
    async def get_scheduled_posts(self, task_id: int = None) -> List[Dict]:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            if task_id:
                async with db.execute('''
                    SELECT * FROM scheduled_posts WHERE task_id = ? AND is_active = 1
                ''', (task_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
            else:
                async with db.execute('''
                    SELECT * FROM scheduled_posts WHERE is_active = 1
                ''') as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
    
    async def delete_scheduled_post(self, schedule_id: int):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute('UPDATE scheduled_posts SET is_active = 0 WHERE schedule_id = ?', (schedule_id,))
            await db.commit()

# Global database instance
db = Database()
