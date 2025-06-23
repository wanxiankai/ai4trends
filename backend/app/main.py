# ===============================================================
# app/main.py
# The main application file that ties everything together.
# ===============================================================
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional
import datetime
import re # Import regular expressions
from .database import create_db_and_tables, get_session, engine
from .models import Config, AnalysisResult, ChatMessage
from .scheduler import scheduler, run_analysis_task
from . import services

app = FastAPI(title="GitHub Trending AI Analyst Backend", version="3.0.0 (Hybrid Intent Parsing)")

origins = [ "http://localhost", "http://localhost:5173", "http://127.0.0.1:5173", "https://ai-trends-463709.web.app"]
app.add_middleware( CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)

@app.on_event("startup")
async def startup_event():
    print("Application starting up...")
    try:
        create_db_and_tables()
        print("Database tables checked/created successfully.")
    except Exception as e:
        print(f"CRITICAL: Database initialization failed: {e}")
        # In a real production app, you might want to exit or handle this more gracefully
        return

    with Session(engine) as session:
        interval_config = session.get(Config, "schedule_interval_minutes")
        try:
            interval = int(interval_config.value) if interval_config else 10
        except (ValueError, TypeError):
            interval = 10
    
    run_time = datetime.datetime.now() + datetime.timedelta(seconds=5)
    scheduler.add_job(run_analysis_task, 'date', run_date=run_time, id="initial_analysis_task")
    print("Initial analysis task scheduled to run in 5 seconds.")

    scheduler.add_job(run_analysis_task, 'interval', minutes=interval, id="recurring_analysis_task")
    scheduler.start()
    print(f"Scheduler started. Recurring analysis task will run every {interval} minutes.")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    print("Scheduler shut down.")

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
    # Pre-process for Chinese numbers and half
    processed_message = message.lower()
    replacements = { "一个半": "1.5", "半": "0.5", "一": "1", "二": "2", "两": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10", }
    for old, new in replacements.items():
        processed_message = processed_message.replace(old, new)

    # Regex to find a number followed by 'hour' or '小时', or a number followed by 'minute'/'分钟' or just a number
    match_hour = re.search(r'(\d+(\.\d+)?)\s*(小时|hour)', processed_message)
    if match_hour:
        return int(float(match_hour.group(1)) * 60)

    match_minute = re.search(r'(\d+(\.\d+)?)\s*(分钟|minute)', processed_message)
    if match_minute:
        return int(float(match_minute.group(1)))
        
    return None

@app.post("/api/chat")
async def handle_chat_with_db(chat_message: ChatMessage, session: Session = Depends(get_session)):
    """Handles chat messages using a hybrid AI (for language) + Regex (for time) approach."""
    message = chat_message.message.lower()
    replies = []
    config_changed = False
    
    # 1. Use AI to parse the language (its specialty)
    new_language = await services.parse_language_with_ai(message)
    if new_language:
        config_to_update = session.get(Config, "trending_language")
        if config_to_update and config_to_update.value != new_language:
            config_to_update.value = new_language
            session.add(config_to_update)
            config_changed = True
            replies.append(f"追踪语言已更新为 **{new_language}**。")

    # 2. Use Regex to parse the frequency (more reliable for structured data)
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
                try:
                    scheduler.modify_job("recurring_analysis_task", trigger='interval', minutes=interval_in_minutes)
                    replies.append(f"任务更新频率已调整为每 **{interval_in_minutes}** 分钟一次。")
                    print(f"Task rescheduled to run every {interval_in_minutes} minutes.")
                except Exception as e:
                    replies.append("抱歉，调整任务频率时出错了。")
                    print(f"Error rescheduling job: {e}")

    # 3. Finalize and respond
    if config_changed:
        session.commit()
    
    if replies:
        response_text = " ".join(replies)
    else:
        response_text = "我收到了你的消息，但似乎没有需要我调整的配置。你可以尝试说：'追踪 java' 或 '每 15 分钟更新一次'。"

    return {"reply": response_text}
