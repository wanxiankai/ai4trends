# ===============================================================
# app/config.py
# New file to handle settings and environment variables.
# ===============================================================
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ai_api_key: str = "default_key"
    github_token: str = "default_token" # New setting for GitHub API

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()