# ===============================================================
# app/database.py
# UPDATED: We no longer call create_db_and_tables here.
# The database is now expected to exist.
# ===============================================================
from sqlmodel import create_engine, Session
import os

# The database file will be copied into this location inside the container.
# For local development, this path won't exist, which is fine.
# In the cloud, it will be at the root of our application code.
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///database.db")

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def get_session():
    with Session(engine) as session:
        yield session