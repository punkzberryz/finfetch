from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

class PriceBar(BaseModel):
    """
    Single price candle (OHLCV).
    """
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: Optional[float] = None
