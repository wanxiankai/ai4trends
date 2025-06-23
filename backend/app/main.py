# ===============================================================
# app/main.py
# The main application file that ties everything together.
# ===============================================================
from fastapi import FastAPI, Depends, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional
import re
from .database import get_session
from .models import Config, AnalysisResult, ChatMessage
from . import services
from .tasks import run_analysis_task

app = FastAPI(title="GitHub Trending AI Analyst Backend", version="4.1.0 (Pre-built DB)")

origins = [ "http://localhost", "http://localhost:5173", "http://127.0.0.1:5173", "https://ai-trends-463709.web.app"]
app.add_middleware( CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)

# --- Public API Endpoints ---
@app.get("/api/config")
def get_config_from_db(session: Session = Depends(get_session)):
    # ... (this endpoint remains the same)
    configs = session.exec(select(Config)).all()
    return {c.key: c.value for c in configs}

@app.get("/api/results", response_model=List[AnalysisResult])
def get_results_from_db(session: Session = Depends(get_session)):
    # ... (this endpoint remains the same)
    statement = select(AnalysisResult).order_by(AnalysisResult.analysis_timestamp.desc()).limit(10)
    results = session.exec(statement).all()
    return results

def _parse_frequency_with_regex(message: str) -> Optional[int]:
    # ... (this function remains the same)
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
    return None

@app.post("/api/chat")
async def handle_chat_with_db(chat_message: ChatMessage, session: Session = Depends(get_session)):
    # ... (this endpoint remains the same)
    message = chat_message.message.lower()
    replies = []
    config_changed = False
    new_language = await services.parse_language_with_ai(message)
    if new_language:
        config_to_update = session.get(Config, "trending_language")
        if config_to_update and config_to_update.value != new_language:
            config_to_update.value = new_language
            session.add(config_to_update)
            config_changed = True
            replies.append(f"追踪语言已更新为 **{new_language}**。")
    interval_in_minutes = _parse_frequency_with_regex(message)
    if interval_in_minutes is not None:
        replies.append(f"频率设置功能当前已由 Cloud Scheduler 管理，请在 Google Cloud 控制台调整。")
    if config_changed:
        session.commit()
    if replies:
        response_text = " ".join(replies)
    else:
        response_text = "我收到了你的消息，但似乎没有需要我调整的配置。你可以尝试说：'追踪 java'。"
    return {"reply": response_text}
    
# --- Internal Task Endpoint ---
@app.post("/api/internal/run-task")
async def trigger_analysis_task(
    background_tasks: BackgroundTasks,
    x_cloud_scheduler: Optional[str] = Header(None)
):
    # ... (this endpoint remains the same)
    if x_cloud_scheduler != "true":
         print("Warning: Task endpoint called without Cloud Scheduler header.")
    print("Task endpoint triggered. Adding analysis task to background.")
    background_tasks.add_task(run_analysis_task)
    return {"status": "success", "message": "Analysis task started in the background."}
