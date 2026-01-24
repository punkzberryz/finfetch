from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class FundamentalsSnapshot(BaseModel):
    """
    Normalized snapshot of company fundamentals.
    """
    symbol: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    
    currency: Optional[str] = None
    market_cap: Optional[int] = None
    
    # Valuation (snapshot)
    trailing_pe: Optional[float] = Field(None, alias="trailingPE")
    forward_pe: Optional[float] = Field(None, alias="forwardPE")
    
    # Raw or extra data not strictly typed
    details: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
