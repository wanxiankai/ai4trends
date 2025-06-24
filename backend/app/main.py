# ===============================================================
# app/main.py
# UPDATED: Simplified startup event, no more APScheduler.
# Removed chat logic for changing frequency as it's now handled by Cloud Scheduler.
# ===============================================================
from fastapi import FastAPI, Depends, Header, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List, Optional
from .database import create_db_and_tables, get_session
from .models import Config, AnalysisResult, ChatMessage
from . import services
from .tasks import run_analysis_task

app = FastAPI(title="GitHub Trending AI Analyst Backend", version="4.0.0 (Cloud-Native)")

origins = [ "http://localhost", "http://localhost:5173", "http://127.0.0.1:5173", "https://ai-trends-463709.web.app"]
app.add_middleware( CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],)

@app.on_event("startup")
def startup_event():
    """A lightweight startup event that only creates DB tables."""
    print("Application starting up...")
    create_db_and_tables()
    print("Application startup complete.")

# --- Public API Endpoints ---
@app.get("/api/config")
def get_config_from_db(session: Session = Depends(get_session)):
    configs = session.exec(select(Config)).all()
    return {c.key: c.value for c in configs}

@app.get("/api/results", response_model=List[AnalysisResult])
def get_results_from_db(session: Session = Depends(get_session)):
    statement = select(AnalysisResult).order_by(AnalysisResult.analysis_timestamp.desc()).limit(10)
    results = session.exec(statement).all()
    return results

@app.post("/api/chat")
async def handle_chat_with_db(chat_message: ChatMessage, session: Session = Depends(get_session)):
    """Handles chat messages to change the language."""
    message = chat_message.message.lower()
    new_language = await services.parse_language_with_ai(message)
    if new_language:
        config_to_update = session.get(Config, "trending_language")
        if config_to_update and config_to_update.value != new_language:
            config_to_update.value = new_language
            session.add(config_to_update)
            session.commit()
            return {"reply": f"好的，我已经将追踪语言更新为 **{new_language}**。"}
    return {"reply": "我收到了你的消息，但目前只支持通过聊天修改追踪语言。"}
    
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