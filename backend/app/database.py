# ===============================================================
# app/database.py
# This file handles all database connection logic.
# ===============================================================
from sqlmodel import create_engine, SQLModel, Session, select
from .models import Config as DBConfig, AnalysisResult as DBAnalysisResult

# For cloud environments, write to the /tmp directory, which is writable.
# The leading double slash is important for absolute paths in sqlite.
DATABASE_URL = "sqlite:////tmp/database.db"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        existing_config = session.get(DBConfig, "trending_language")
        if not existing_config:
            default_language = DBConfig(key="trending_language", value="python")
            default_interval = DBConfig(key="schedule_interval_minutes", value="10")
            session.add(default_language)
            session.add(default_interval)
            session.commit()

def get_session():
    with Session(engine) as session:
        yield session