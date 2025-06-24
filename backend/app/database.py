# ===============================================================
# app/database.py
# UPDATED: Using the writable /tmp directory for the database in a cloud environment.
# And re-introducing the table creation logic to run at startup.
# ===============================================================
from sqlmodel import create_engine, SQLModel, Session
from .models import Config

DATABASE_URL = "sqlite:////tmp/database.db"
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def create_db_and_tables():
    print("Checking and creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("Tables check/creation complete.")
    with Session(engine) as session:
        existing_config = session.get(Config, "trending_language")
        if not existing_config:
            print("Populating initial configuration...")
            # Set default language to 'all' for better initial data
            default_language = Config(key="trending_language", value="all")
            default_interval = Config(key="schedule_interval_minutes", value="10")
            session.add(default_language)
            session.add(default_interval)
            session.commit()
            print("Initial configuration populated.")
        else:
            print("Configuration already exists.")

def get_session():
    with Session(engine) as session:
        yield session