# This file handles all database connection logic.
# ===============================================================
from sqlmodel import create_engine, SQLModel, Session, select
from .models import Config, AnalysisResult

# Define the database file. It will be created in the same directory.
DATABASE_URL = "sqlite:///database.db"

# The engine is the central point of communication with the database.
# connect_args is needed for SQLite to allow it to be used by multiple threads.
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

def create_db_and_tables():
    """
    Initializes the database and creates tables if they don't exist.
    It also populates the initial configuration.
    """
    SQLModel.metadata.create_all(engine)

    # Populate initial config if it doesn't exist
    with Session(engine) as session:
        # Check if config already exists
        statement = select(Config).where(Config.key == "trending_language")
        existing_config = session.exec(statement).first()
        if not existing_config:
            # Add default configuration
            default_language = Config(key="trending_language", value="python")
            default_interval = Config(key="schedule_interval_hours", value="1")
            session.add(default_language)
            session.add(default_interval)
            session.commit()

def get_session():
    """
    Dependency injection function to get a database session for each request.
    This ensures each request has its own isolated session.
    """
    with Session(engine) as session:
        yield session
