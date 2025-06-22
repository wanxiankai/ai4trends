# ===============================================================
# app/main.py
# The main application file that ties everything together.
# ===============================================================
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from typing import List
from .database import create_db_and_tables, get_session, engine
from .models import Config, AnalysisResult, ChatMessage
from .scheduler import scheduler, run_analysis_task

app = FastAPI(title="GitHub Trending AI Analyst Backend", version="1.2.1 (Improved Language Detection)")

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
    configs = session.exec(select(Config)).all()
    return {c.key: c.value for c in configs}

@app.get("/api/results", response_model=List[AnalysisResult])
def get_results_from_db(session: Session = Depends(get_session)):
    statement = select(AnalysisResult).order_by(AnalysisResult.analysis_timestamp.desc()).limit(10)
    results = session.exec(statement).all()
    return results

@app.post("/api/chat")
def handle_chat_with_db(chat_message: ChatMessage, session: Session = Depends(get_session)):
    message = chat_message.message.lower()
    response_text = "抱歉，我不太理解你的意思。你可以尝试说：'追踪[语言]'或'频率改为[数字]分钟/小时'。"
    config_changed = False

    # UPDATED: Improved language detection logic
    if '追踪' in message or 'track' in message:
        languages = ['javascript', 'python', 'typescript', 'go', 'rust', 'java', 'c++']
        # Instead of splitting the message, check if any known language is a substring of the message
        found_lang = next((lang for lang in languages if lang in message), None)
        
        if found_lang:
            # Handle the "java" vs "javascript" ambiguity. Prefer the longer match.
            if 'javascript' in message:
                found_lang = 'javascript'

            config_to_update = session.get(Config, "trending_language")
            if config_to_update:
                config_to_update.value = found_lang
                session.add(config_to_update)
                config_changed = True
                response_text = f"好的！我已经将追踪的语言更新为 **{found_lang}**。"
    
    elif any(unit in message for unit in ['分钟', '小时', 'minute', 'hour', '频率', 'interval']):
        import re
        match = re.search(r'(\d+(\.\d+)?)', message)
        
        if match:
            value = float(match.group(0))
            interval_in_minutes = 0

            if '小时' in message or 'hour' in message:
                interval_in_minutes = int(value * 60)
            else:
                interval_in_minutes = int(value)
            
            if interval_in_minutes < 1:
                response_text = "更新频率太快了！请设置一个不小于1分钟的间隔。"
            else:
                config_to_update = session.get(Config, "schedule_interval_minutes")
                if config_to_update:
                    config_to_update.value = str(interval_in_minutes)
                    session.add(config_to_update)
                    config_changed = True
                    try:
                        scheduler.reschedule_job("analysis_task", trigger='interval', minutes=interval_in_minutes)
                        response_text = f"收到！我已经将任务更新频率调整为每 **{interval_in_minutes}** 分钟一次。"
                        print(f"Task rescheduled to run every {interval_in_minutes} minutes.")
                    except Exception as e:
                        response_text = "抱歉，调整任务频率时出错了。"
                        print(f"Error rescheduling job: {e}")
                else:
                    response_text = "找不到频率配置项。"
        else:
            response_text = "我没有找到有效的时间数字，请重试。例如：'10分钟'或'0.5小时'。"

    if config_changed:
        session.commit()

    return {"reply": response_text}
