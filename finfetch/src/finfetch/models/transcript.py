from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TranscriptSection(BaseModel):
    """Single speaker section within a transcript."""

    speaker: str
    text: str
    role: Optional[str] = None


class Transcript(BaseModel):
    """Normalized earnings-call transcript."""

    provider: str = "yahoo"
    url: str
    symbol: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    quarter: Optional[str] = None
    event_date: Optional[date] = None
    published_at: Optional[datetime] = None
    speakers: List[str] = Field(default_factory=list)
    sections: List[TranscriptSection] = Field(default_factory=list)
    full_text: str = ""
    raw_html: Optional[str] = None
