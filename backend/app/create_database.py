# ===============================================================
# create_database.py
# NEW FILE: Create this file in your 'backend' directory.
# We will run this file LOCALLY ONCE to create the database.
# ===============================================================
import os
from app.database import create_db_and_tables, DATABASE_URL

# The DATABASE_URL in database.py points to /tmp, which is for the cloud.
# For local creation, we want it in the current directory.
LOCAL_DB_FILE = "database.db"

def main():
    """
    Creates the database file and tables locally.
    """
    # Temporarily override the DATABASE_URL to create the file locally
    # This is a bit of a hack, but effective for our one-time setup.
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{LOCAL_DB_FILE}"
    
    # Check if the DB file already exists to avoid overwriting
    if os.path.exists(LOCAL_DB_FILE):
        print(f"Database file '{LOCAL_DB_FILE}' already exists. Skipping creation.")
    else:
        print(f"Creating new database file at '{LOCAL_DB_FILE}'...")
        # This will now use the overridden URL
        from app.database import engine, SQLModel
        SQLModel.metadata.create_all(engine)
        
        # We also need to populate the initial config
        from sqlmodel import Session
        from app.models import Config
        
        with Session(engine) as session:
            default_language = Config(key="trending_language", value="python")
            default_interval = Config(key="schedule_interval_minutes", value="10")
            session.add(default_language)
            session.add(default_interval)
            session.commit()
            
        print("Database and initial configuration created successfully.")

    # Restore original environment variable if it existed
    if original_db_url:
        os.environ["DATABASE_URL"] = original_db_url
    else:
        del os.environ["DATABASE_URL"]

if __name__ == "__main__":
    # This check is not strictly necessary for this script, but good practice
    from app.database import create_db_and_tables
    main()
