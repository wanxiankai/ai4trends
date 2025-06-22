# ===============================================================
# app/database.py
# This file handles all database connection logic.
# ===============================================================
from sqlmodel import create_engine, SQLModel, Session, select
from .models import Config as DBConfig, AnalysisResult as DBAnalysisResult

DATABASE_URL = "sqlite:///database.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False}) # Set echo=False for cleaner logs

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        existing_config = session.get(DBConfig, "trending_language")
        if not existing_config:
            default_language = DBConfig(key="trending_language", value="python")
            default_interval = DBConfig(key="schedule_interval_hours", value="1")
            session.add(default_language)
            session.add(default_interval)
            session.commit()

def get_session():
    with Session(engine) as session:
        yield session