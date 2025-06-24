# ===============================================================
# app/main.py
# UPDATED: Simplified startup event, no more APScheduler.
# Removed chat logic for changing frequency as it's now handled by Cloud Scheduler.
# ===============================================================
from fastapi import FastAPI, Depends, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional
import re
from .database import create_db_and_tables, get_session
from .models import Config, AnalysisResult, ChatMessage
from . import services
from .tasks import run_analysis_task

app = FastAPI(title="GitHub Trending AI Analyst Backend", version="5.1.0 (Final Fix)")

origins = [ "http://localhost", "http://localhost:5173", "http://127.0.0.1:5173", "https://ai-trends-463709.web.app"]
app.add_middleware( CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)

@app.on_event("startup")
def startup_event():
    """A lightweight startup event that only creates DB tables."""
    print("Application starting up...")
    create_db_and_tables()
    print("Application startup complete.")

@app.get("/api/config")
def get_config_from_db(session: Session = Depends(get_session)):
    configs = session.exec(select(Config)).all()
    return {c.key: c.value for c in configs}

@app.get("/api/results", response_model=List[AnalysisResult])
def get_results_from_db(session: Session = Depends(get_session)):
    statement = select(AnalysisResult).order_by(AnalysisResult.analysis_timestamp.desc()).limit(10)
    results = session.exec(statement).all()
    return results

def _parse_frequency_with_regex(message: str) -> Optional[int]:
    """Extracts time interval in minutes from a message using Regex."""
    processed_message = message.lower()
    replacements = { "一个半": "1.5", "半": "0.5", "一": "1", "二": "2", "两": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10", }
    for old, new in replacements.items():
        processed_message = processed_message.replace(old, new)
    
    match_hour = re.search(r'(\d+(\.\d+)?)\s*(小时|hour)', processed_message)
    if match_hour:
        return int(float(match_hour.group(1)) * 60)

    match_minute = re.search(r'(\d+(\.\d+)?)\s*(分钟|minute)', processed_message)
    if match_minute:
        return int(float(match_minute.group(1)))
    
    match_number_only = re.search(r'(\d+(\.\d+)?)', processed_message)
    if match_number_only:
         if "更新" in message or "每" in message or "every" in message:
              return int(float(match_number_only.group(1)))

    return None

@app.post("/api/chat")
async def handle_chat_with_db(chat_message: ChatMessage, session: Session = Depends(get_session)):
    """Handles chat messages to change the language or frequency."""
    message = chat_message.message.lower()
    replies = []
    config_changed = False
    
    # 1. Use AI to parse the language
    new_language = await services.parse_language_with_ai(message)
    if new_language:
        config_to_update = session.get(Config, "trending_language")
        if config_to_update and config_to_update.value != new_language:
            config_to_update.value = new_language
            session.add(config_to_update)
            config_changed = True
            replies.append(f"追踪语言已更新为 **{new_language}**。")

    # 2. Use Regex to parse the frequency
    interval_in_minutes = _parse_frequency_with_regex(message)
    if interval_in_minutes is not None:
        if interval_in_minutes < 1:
            replies.append("更新频率太快了！请设置一个不小于1分钟的间隔。")
        else:
            config_to_update = session.get(Config, "schedule_interval_minutes")
            if config_to_update and config_to_update.value != str(interval_in_minutes):
                config_to_update.value = str(interval_in_minutes)
                session.add(config_to_update)
                config_changed = True
                # FIX: Correctly add the reply for frequency changes
                replies.append(f"任务更新频率将在下次由 Cloud Scheduler 触发时生效，请在 Cloud 控制台调整为每 **{interval_in_minutes}** 分钟一次。")

    # 3. Finalize and respond
    if config_changed:
        session.commit()
    
    if replies:
        response_text = " ".join(replies)
    else:
        # Final fallback message
        response_text = "我收到了你的消息，但似乎没有识别到需要我调整的配置。你可以尝试说：'追踪 java'。"

    return {"reply": response_text}
    
# --- Internal Task Endpoint ---
@app.post("/api/internal/run-task")
async def trigger_analysis_task(
    background_tasks: BackgroundTasks,
    x_cloud_scheduler: Optional[str] = Header(None)
):
    """An internal endpoint to trigger the analysis task, called by Cloud Scheduler."""
    if x_cloud_scheduler != "true":
         print("Warning: Task endpoint called without Cloud Scheduler header.")
    print("Task endpoint triggered. Adding analysis task to background.")
    background_tasks.add_task(run_analysis_task)
    return {"status": "success", "message": "Analysis task started in the background."}
