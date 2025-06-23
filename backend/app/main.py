# ===============================================================
# app/main.py
# The main application file that ties everything together.
# ===============================================================
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional
import datetime # Import datetime for scheduling

from .database import create_db_and_tables, get_session, engine
from .models import Config, AnalysisResult, ChatMessage
from .scheduler import scheduler, run_analysis_task
from . import services # Import the services module

app = FastAPI(title="GitHub Trending AI Analyst Backend", version="2.4.0 (Robust Startup)")

origins = [ "http://localhost", "http://localhost:5173", "http://127.0.0.1:5173", "https://ai-trends-463709.web.app"]
app.add_middleware( CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)


@app.on_event("startup")
async def startup_event():
    """
    On startup, create DB, and schedule tasks to run in the background.
    This allows the web server to start quickly without being blocked.
    """
    print("Application starting up...")
    create_db_and_tables()

    with Session(engine) as session:
        interval_config = session.get(Config, "schedule_interval_minutes")
        try:
            interval = int(interval_config.value) if interval_config else 10
        except (ValueError, TypeError):
            interval = 10
    
    # Schedule the first run to happen 5 seconds after startup.
    # This gives the server time to become healthy before heavy work begins.
    run_time = datetime.datetime.now() + datetime.timedelta(seconds=5)
    scheduler.add_job(run_analysis_task, 'date', run_date=run_time, id="initial_analysis_task")
    print("Initial analysis task scheduled to run in 5 seconds.")

    # Schedule the recurring job to run every N minutes
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

def preprocess_message_for_ai(message: str) -> str:
    """Replaces Chinese number words and units with Arabic numerals for better AI parsing."""
    replacements = { "一个半": "1.5", "半": "0.5", "一": "1", "二": "2", "两": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10", }
    for old, new in replacements.items():
        message = message.replace(old, new)
    return message

@app.post("/api/chat")
async def handle_chat_with_db(chat_message: ChatMessage, session: Session = Depends(get_session)):
    """
    Handles chat messages by pre-processing, parsing with AI, then executing.
    """
    original_message = chat_message.message.lower()
    processed_message = preprocess_message_for_ai(original_message)
    print(f"Original message: '{original_message}' -> Processed message: '{processed_message}'")

    intent_data = await services.parse_intent_with_ai(processed_message)

    if not intent_data:
        return {"reply": "抱歉，我在理解你的请求时遇到了一个问题，请稍后再试。"}

    replies = []
    config_changed = False
    
    new_language = intent_data.get("language")
    if new_language:
        config_to_update = session.get(Config, "trending_language")
        if config_to_update and config_to_update.value != new_language:
            config_to_update.value = new_language
            session.add(config_to_update)
            config_changed = True
            replies.append(f"追踪语言已更新为 **{new_language}**。")

    time_value = intent_data.get("time_value")
    time_unit = intent_data.get("time_unit")
    
    # Fallback logic: If AI missed the unit, check the original message
    if time_value is not None and time_unit is None:
        if "小时" in original_message or "hour" in original_message:
            time_unit = "hours"
            print("Fallback applied: Detected 'hours' unit from original message.")
    
    if time_value is not None:
        interval_in_minutes = 0
        unit_to_check = time_unit or "minutes" # Default to minutes if still no unit
        
        if unit_to_check == "hours":
            interval_in_minutes = int(float(time_value) * 60)
        else:
            interval_in_minutes = int(float(time_value))

        if interval_in_minutes < 1:
            replies.append("更新频率太快了！请设置一个不小于1分钟的间隔。")
        else:
            config_to_update = session.get(Config, "schedule_interval_minutes")
            if config_to_update and config_to_update.value != str(interval_in_minutes):
                config_to_update.value = str(interval_in_minutes)
                session.add(config_to_update)
                config_changed = True
                try:
                    # Use modify_job to change the interval of the existing recurring task
                    scheduler.modify_job("recurring_analysis_task", trigger='interval', minutes=interval_in_minutes)
                    replies.append(f"任务更新频率已调整为每 **{interval_in_minutes}** 分钟一次。")
                    print(f"Task rescheduled to run every {interval_in_minutes} minutes.")
                except Exception as e:
                    replies.append("抱歉，调整任务频率时出错了。")
                    print(f"Error rescheduling job: {e}")

    if config_changed:
        session.commit()
    
    if replies:
        response_text = " ".join(replies)
    else:
        response_text = "我收到了你的消息，但似乎没有需要我调整的配置。你可以尝试说：'追踪 java' 或 '每 15 分钟更新一次'。"

    return {"reply": response_text}