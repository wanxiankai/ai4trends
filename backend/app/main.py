# ===============================================================
# app/main.py
# The main application file that ties everything together.
# ===============================================================
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional
from .database import create_db_and_tables, get_session, engine
from .models import Config, AnalysisResult, ChatMessage
from .scheduler import scheduler, run_analysis_task
from . import services # Import the services module

app = FastAPI(title="GitHub Trending AI Analyst Backend", version="2.0.0 (AI-Powered Intent Parsing)")

# ... (CORS middleware remains the same)
origins = [ "http://localhost", "http://localhost:5173", "http://127.0.0.1:5173" ]
app.add_middleware( CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)


@app.on_event("startup")
async def startup_event():
    # ... (startup logic remains the same)
    print("Application starting up...")
    create_db_and_tables()

    with Session(engine) as session:
        interval_config = session.get(Config, "schedule_interval_minutes")
        try:
            interval = int(interval_config.value) if interval_config else 10
        except (ValueError, TypeError):
            interval = 10
    
    print("Performing initial data analysis on startup...")
    await run_analysis_task()
    
    scheduler.add_job(run_analysis_task, 'interval', minutes=interval, id="analysis_task")
    scheduler.start()
    print(f"Scheduler started. Analysis task will run every {interval} minutes.")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    print("Scheduler shut down.")

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

# UPDATED: The entire chat handler is now refactored.
@app.post("/api/chat")
async def handle_chat_with_db(chat_message: ChatMessage, session: Session = Depends(get_session)):
    """
    Handles chat messages by first parsing intent with AI, then executing changes.
    """
    # 1. Get user's intent from AI
    intent_data = await services.parse_intent_with_ai(chat_message.message)

    if not intent_data:
        return {"reply": "抱歉，我在理解你的请求时遇到了一个问题，请稍后再试。"}

    replies = []
    config_changed = False
    
    # 2. Process language change intent
    new_language = intent_data.get("language")
    if new_language:
        config_to_update = session.get(Config, "trending_language")
        if config_to_update and config_to_update.value != new_language:
            config_to_update.value = new_language
            session.add(config_to_update)
            config_changed = True
            replies.append(f"追踪语言已更新为 **{new_language}**。")

    # 3. Process frequency change intent
    new_interval = intent_data.get("interval_minutes")
    if new_interval is not None:
        interval_in_minutes = int(new_interval)
        if interval_in_minutes < 1:
            replies.append("更新频率太快了！请设置一个不小于1分钟的间隔。")
        else:
            config_to_update = session.get(Config, "schedule_interval_minutes")
            if config_to_update and config_to_update.value != str(interval_in_minutes):
                config_to_update.value = str(interval_in_minutes)
                session.add(config_to_update)
                config_changed = True
                try:
                    scheduler.reschedule_job("analysis_task", trigger='interval', minutes=interval_in_minutes)
                    replies.append(f"任务更新频率已调整为每 **{interval_in_minutes}** 分钟一次。")
                    print(f"Task rescheduled to run every {interval_in_minutes} minutes.")
                except Exception as e:
                    replies.append("抱歉，调整任务频率时出错了。")
                    print(f"Error rescheduling job: {e}")

    # 4. Finalize and respond
    if config_changed:
        session.commit()
    
    if replies:
        response_text = " ".join(replies)
    else:
        response_text = "我收到了你的消息，但似乎没有需要我调整的配置。你可以尝试说：'追踪 java' 或 '每 15 分钟更新一次'。"

    return {"reply": response_text}
