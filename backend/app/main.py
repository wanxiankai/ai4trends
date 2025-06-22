# ===============================================================
# app/main.py
# The main application file that ties everything together.
# ===============================================================
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from typing import List
import asyncio

from .database import create_db_and_tables, get_session
from .models import Config, AnalysisResult, ChatMessage
from .scheduler import scheduler, run_analysis_task

app = FastAPI(title="GitHub Trending AI Analyst Backend", version="1.0.0")

# CORS middleware configuration (no changes)
# ...
origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """On startup, create DB, run task once immediately, then schedule it."""
    print("Application starting up...")
    create_db_and_tables()
    
    print("Performing initial data analysis on startup...")
    # Run the task once immediately to populate the database
    await run_analysis_task()
    
    # Schedule the job to run every 10 minutes
    scheduler.add_job(run_analysis_task, 'interval', minutes=10, id="analysis_task")
    scheduler.start()
    print("Scheduler started. Analysis task will run every 10 minutes.")

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    print("Scheduler shut down.")

# API endpoints (no changes in their code)
# ...

@app.get("/api/config")
def get_config_from_db(session: Session = Depends(get_session)):
    """Fetches configuration from the database."""
    configs = session.exec(select(Config)).all()
    return {c.key: c.value for c in configs}

@app.get("/api/results", response_model=List[AnalysisResult])
def get_results_from_db(session: Session = Depends(get_session)):
    """Fetches the latest analysis results from the database."""
    statement = select(AnalysisResult).order_by(AnalysisResult.analysis_timestamp.desc()).limit(10)
    results = session.exec(statement).all()
    return results

@app.post("/api/chat")
def handle_chat_with_db(chat_message: ChatMessage, session: Session = Depends(get_session)):
    """Handles chat messages and updates the configuration in the database."""
    message = chat_message.message.lower()
    response_text = "抱歉，我不太理解你的意思。你可以尝试说：'追踪[语言]'或'频率改为[数字]小时'。"
    # ... (logic remains the same)
    config_changed = False
    if '追踪' in message or 'track' in message:
        languages = ['javascript', 'python', 'typescript', 'go', 'rust', 'java', 'c++']
        found_lang = next((lang for lang in languages if lang in message), None)
        if found_lang:
            config_to_update = session.get(Config, "trending_language")
            if config_to_update:
                config_to_update.value = found_lang
                session.add(config_to_update)
                config_changed = True
                response_text = f"好的！我已经将追踪的语言更新为 **{found_lang}**。"

    elif '小时' in message or '频率' in message or 'interval' in message:
        import re
        match = re.search(r'\d+', message)
        if match:
            hours = int(match.group(0))
            if hours > 0:
                config_to_update = session.get(Config, "schedule_interval_hours")
                if config_to_update:
                    config_to_update.value = str(hours)
                    session.add(config_to_update)
                    config_changed = True
                    response_text = f"收到！我已经将任务更新频率调整为每 **{hours}** 小时一次。"

    if config_changed:
        session.commit()

    return {"reply": response_text}
