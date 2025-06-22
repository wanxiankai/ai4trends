# ===============================================================
# app/models.py
# This file defines the structure of our database tables and API models.
# ===============================================================
from typing import List, Optional
from sqlmodel import Field, SQLModel, JSON, Column
import datetime

class Config(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str

class AnalysisResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    repo_name: str = Field(index=True)
    repo_url: str
    analysis_timestamp: datetime.datetime
    one_liner_summary: str
    tech_stack: List[str] = Field(sa_column=Column(JSON))
    key_features: List[str] = Field(sa_column=Column(JSON))
    community_focus: List[str] = Field(sa_column=Column(JSON))

class ChatMessage(SQLModel):
    message: str
