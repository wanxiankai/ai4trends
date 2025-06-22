# The main application file that ties everything together.
# ===============================================================
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List

# Import from our other modules
from .database import create_db_and_tables, get_session
from .models import Config, AnalysisResult, ChatMessage # ChatMessage is now defined in models.py
from .scheduler import scheduler, run_analysis_task

app = FastAPI(
    title="GitHub Trending AI Analyst Backend",
    description="Backend service with a database and scheduled tasks.",
    version="0.2.0",
)

# CORS middleware configuration
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
def startup_event():
    """
    Actions to perform on application startup.
    """
    print("Application starting up...")
    # 1. Create database and tables
    create_db_and_tables()
    # 2. Add the job to the scheduler. For testing, it runs every 1 minute.
    #    For production, change `minutes=1` to `hours=1`.
    scheduler.add_job(run_analysis_task, 'interval', minutes=1, id="analysis_task")
    # 3. Start the scheduler
    scheduler.start()
    print("Scheduler started. Analysis task will run every 1 minute.")

@app.on_event("shutdown")
def shutdown_event():
    """
    Actions to perform on application shutdown.
    """
    print("Scheduler shutting down...")
    scheduler.shutdown()

# --- API Endpoints (now connected to the database) ---

@app.get("/api/config")
def get_config_from_db(session: Session = Depends(get_session)):
    """
    Fetches configuration from the database.
    """
    configs = session.exec(select(Config)).all()
    # Convert list of config objects to a dictionary
    return {c.key: c.value for c in configs}

@app.get("/api/results", response_model=List[AnalysisResult])
def get_results_from_db(session: Session = Depends(get_session)):
    """
    Fetches the latest analysis results from the database.
    """
    # Order by timestamp descending to get the newest first, limit to 10
    statement = select(AnalysisResult).order_by(AnalysisResult.analysis_timestamp.desc()).limit(10)
    results = session.exec(statement).all()
    return results

@app.post("/api/chat")
def handle_chat_with_db(chat_message: ChatMessage, session: Session = Depends(get_session)):
    """
    Handles chat messages and updates the configuration in the database.
    """
    message = chat_message.message.lower()
    response_text = "抱歉，我不太理解你的意思。你可以尝试说：'追踪[语言]'或'频率改为[数字]小时'。"

    config_changed = False
    
    # Logic to understand user intent and update DB
    if '追踪' in message or 'track' in message:
        # ... (same logic as before)
        languages = ['javascript', 'python', 'typescript', 'go', 'rust', 'java', 'c++']
        found_lang = next((lang for lang in languages if lang in message), None)
        if found_lang:
            config_to_update = session.get(Config, "trending_language")
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
                config_to_update.value = str(hours)
                session.add(config_to_update)
                config_changed = True
                response_text = f"收到！我已经将任务更新频率调整为每 **{hours}** 小时一次。"

    if config_changed:
        session.commit()

    return {"reply": response_text}
