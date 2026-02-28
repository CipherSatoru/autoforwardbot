"""
Telegram Forward Bot - Scheduler Module
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
from typing import Dict, List
import config
from database import db

class BotScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=config.SCHEDULER_TIMEZONE)
        self.active_tasks = {}  # Store job IDs for each task
    
    def start(self):
        """Start the scheduler"""
        self.scheduler.start()
    
    def shutdown(self):
        """Shutdown the scheduler"""
        self.scheduler.shutdown()
    
    # ========== POWER ON/OFF SCHEDULE ==========
    def schedule_power_on(self, task_id: int, time_str: str, callback):
        """Schedule task to turn on at specific time"""
        try:
            # Parse time string (HH:MM format)
            hour, minute = map(int, time_str.split(':'))
            
            job_id = f"power_on_{task_id}"
            
            # Remove existing job if any
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Add new job
            self.scheduler.add_job(
                callback,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=job_id,
                args=[task_id, True],
                replace_existing=True
            )
            
            return True
        except Exception as e:
            print(f"Schedule power on error: {e}")
            return False
    
    def schedule_power_off(self, task_id: int, time_str: str, callback):
        """Schedule task to turn off at specific time"""
        try:
            hour, minute = map(int, time_str.split(':'))
            
            job_id = f"power_off_{task_id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            self.scheduler.add_job(
                callback,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=job_id,
                args=[task_id, False],
                replace_existing=True
            )
            
            return True
        except Exception as e:
            print(f"Schedule power off error: {e}")
            return False
    
    def remove_power_schedule(self, task_id: int):
        """Remove power on/off schedule for a task"""
        on_job_id = f"power_on_{task_id}"
        off_job_id = f"power_off_{task_id}"
        
        for job_id in [on_job_id, off_job_id]:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
    
    # ========== DELAYED FORWARD ==========
    def schedule_delayed_forward(self, message_id: int, chat_id: int, 
                                 delay_seconds: int, callback):
        """Schedule a message to be forwarded after delay"""
        try:
            job_id = f"delayed_{message_id}_{chat_id}"
            
            # Schedule one-time job
            self.scheduler.add_job(
                callback,
                'date',
                run_date=datetime.now(pytz.UTC).replace(
                    second=datetime.now(pytz.UTC).second + delay_seconds
                ),
                id=job_id,
                args=[message_id, chat_id],
                replace_existing=True
            )
            
            return True
        except Exception as e:
            print(f"Schedule delayed forward error: {e}")
            return False
    
    # ========== AUTO POST SCHEDULER ==========
    def schedule_auto_post(self, schedule_id: int, schedule_time: str, 
                          is_recurring: bool, recurrence_pattern: str, callback):
        """Schedule an auto post"""
        try:
            job_id = f"auto_post_{schedule_id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # Parse schedule time
            dt = datetime.fromisoformat(schedule_time)
            
            if is_recurring and recurrence_pattern:
                # Parse recurrence pattern (e.g., "daily", "weekly", "monthly")
                if recurrence_pattern == 'daily':
                    trigger = CronTrigger(hour=dt.hour, minute=dt.minute)
                elif recurrence_pattern == 'weekly':
                    trigger = CronTrigger(day_of_week=dt.weekday(), hour=dt.hour, minute=dt.minute)
                elif recurrence_pattern == 'monthly':
                    trigger = CronTrigger(day=dt.day, hour=dt.hour, minute=dt.minute)
                else:
                    trigger = CronTrigger(hour=dt.hour, minute=dt.minute)
                
                self.scheduler.add_job(
                    callback,
                    trigger=trigger,
                    id=job_id,
                    args=[schedule_id],
                    replace_existing=True
                )
            else:
                # One-time post
                self.scheduler.add_job(
                    callback,
                    'date',
                    run_date=dt,
                    id=job_id,
                    args=[schedule_id],
                    replace_existing=True
                )
            
            return True
        except Exception as e:
            print(f"Schedule auto post error: {e}")
            return False
    
    def remove_auto_post(self, schedule_id: int):
        """Remove an auto post schedule"""
        job_id = f"auto_post_{schedule_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
    
    # ========== CLONE SOURCE SCHEDULER ==========
    def schedule_clone_task(self, task_id: int, interval_minutes: int, callback):
        """Schedule periodic cloning of source chat"""
        try:
            job_id = f"clone_{task_id}"
            
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            self.scheduler.add_job(
                callback,
                'interval',
                minutes=interval_minutes,
                id=job_id,
                args=[task_id],
                replace_existing=True
            )
            
            return True
        except Exception as e:
            print(f"Schedule clone error: {e}")
            return False
    
    def remove_clone_schedule(self, task_id: int):
        """Remove clone schedule"""
        job_id = f"clone_{task_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
    
    # ========== GET SCHEDULED JOBS ==========
    def get_task_jobs(self, task_id: int) -> List[str]:
        """Get all job IDs for a task"""
        jobs = []
        for job in self.scheduler.get_jobs():
            if str(task_id) in job.id:
                jobs.append(job.id)
        return jobs
    
    def is_task_scheduled(self, task_id: int) -> bool:
        """Check if task has any scheduled jobs"""
        return len(self.get_task_jobs(task_id)) > 0

# Global scheduler instance
scheduler = BotScheduler()
