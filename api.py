from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import hmac
import hashlib
import json
from urllib.parse import parse_qs
from typing import List, Optional
import config
from database import db

app = FastAPI(title="Platinum Forwarder API")

# Enable CORS for the Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your Mini App URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def validate_telegram_data(init_data: str):
    """Validate data received from Telegram Mini App"""
    try:
        vals = {k: v[0] for k, v in parse_qs(init_data).items()}
        hash_str = vals.pop('hash', None)
        if not hash_str:
            return False
            
        data_check_string = "
".join([f"{k}={v}" for k, v in sorted(vals.items())])
        secret_key = hmac.new("WebAppData".encode(), config.BOT_TOKEN.encode(), hashlib.sha256).digest()
        hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        if hmac_hash != hash_str:
            return False
            
        user_data = json.loads(vals.get('user', '{}'))
        return user_data
    except Exception:
        return False

async def get_current_user(authorization: Optional[str] = Header(None)):
    """Dependency to get and validate user from Telegram header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing initData")
    
    user = validate_telegram_data(authorization)
    if not user:
        raise HTTPException(status_code=403, detail="Invalid Telegram data")
    return user

@app.get("/health")
async def health():
    return {"status": "ok"}

# --- API ENDPOINTS ---

@app.get("/api/tasks")
async def get_tasks(user=Depends(get_current_user)):
    """Fetch all tasks for the user"""
    tasks = await db.get_user_tasks(user['id'])
    return tasks

@app.post("/api/tasks")
async def create_task(source_id: int, dest_id: int, user=Depends(get_current_user)):
    """Create a new task from Mini App"""
    task_id = await db.create_task(
        user_id=user['id'],
        source_chat_id=source_id,
        source_chat_title=f"Chat {source_id}",
        destination_chat_id=dest_id,
        destination_chat_title=f"Chat {dest_id}"
    )
    return {"status": "success", "task_id": task_id}

@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: int, settings: dict, user=Depends(get_current_user)):
    """Update task settings (toggle, delay, etc.)"""
    task = await db.get_task(task_id)
    if not task or task['user_id'] != user['id']:
        raise HTTPException(status_code=404, detail="Task not found")
        
    await db.update_task(task_id, **settings)
    return {"status": "updated"}

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, user=Depends(get_current_user)):
    """Delete task from Mini App"""
    task = await db.get_task(task_id)
    if not task or task['user_id'] != user['id']:
        raise HTTPException(status_code=404, detail="Task not found")
        
    await db.delete_task(task_id)
    return {"status": "deleted"}

@app.get("/api/stats")
async def get_stats(user=Depends(get_current_user)):
    """Get user stats for the dashboard"""
    stats = await db.get_stats(user['id'])
    return stats
