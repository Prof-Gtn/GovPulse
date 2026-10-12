"""
GovPulse API — Data models (Pydantic schemas)
"""

from typing import List, Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    name: str
    role: str
    ministry: Optional[str] = None


class Story(BaseModel):
    source: str
    headline: str
    url: Optional[str] = None
    body: Optional[str] = None
    page: Optional[str] = None
    ai_summary: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_confidence: Optional[float] = None
    government_source: Optional[str] = None
    oma: List[str] = []
    entities: Optional[dict] = None
    scraped_at: Optional[str] = None


class ResponseDraft(BaseModel):
    headline: str
    oma: List[str]
    sentiment: str
    response: dict


class ApproveRequest(BaseModel):
    headline: str
    ministry: str
    final_text: str


class PipelineRunRequest(BaseModel):
    run_scraper: bool = True