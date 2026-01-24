from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class NewsItem(BaseModel):
    """
    Normalized news item.
    """
    id: str  # Stable hash
    title: str
    url: str
    published_at: datetime
    source: str
    summary: Optional[str] = None
    tickers: List[str] = []
    
    provider: str = "yahoo"
