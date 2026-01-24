import yfinance as yf
import logging
from typing import List, Dict, Any
from ..errors import ProviderError
from ..models.fundamentals import FundamentalsSnapshot
from ..models.prices import PriceBar
from ..models.news import NewsItem
from datetime import datetime, date

logger = logging.getLogger(__name__)

def fetch_fundamentals(ticker: str) -> FundamentalsSnapshot:
    """Fetch fundamentals from Yahoo Finance."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        
        # Validation: yfinance often returns empty dict if not found, 
        # or minimal data. strict validation might fail, so we be permissive.
        if not info or info.get('regularMarketPrice') is None:
             # This heuristic might need tuning
             pass 

        return FundamentalsSnapshot(
            symbol= info.get('symbol', ticker),
            name=info.get('longName'),
            sector=info.get('sector'),
            industry=info.get('industry'),
            currency=info.get('currency'),
            market_cap=info.get('marketCap'),
            trailingPE=info.get('trailingPE'),
            forwardPE=info.get('forwardPE'),
            details=info
        )
    except Exception as e:
        logger.error(f"Failed to fetch fundamentals for {ticker}: {e}")
        raise ProviderError(f"Yahoo fetch failed: {e}")

def fetch_prices(ticker: str, period: str = "1mo", interval: str = "1d") -> List[PriceBar]:
    """Fetch price history."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        
        if df.empty:
            logger.warning(f"No price data for {ticker}")
            return []
            
        bars = []
        # df.index is typically DatetimeIndex, but timezone aware
        for dt, row in df.iterrows():
            # Convert timestamp to date
            d = dt.date()
            
            bars.append(PriceBar(
                date=d,
                open=row['Open'],
                high=row['High'],
                low=row['Low'],
                close=row['Close'],
                volume=int(row['Volume']),
                adj_close=None # yfinance 'Close' is often adjusted or needs auto_adjust=False
            ))
        
        return bars
    except Exception as e:
        logger.error(f"Failed to fetch prices for {ticker}: {e}")
        raise ProviderError(f"Yahoo prices failed: {e}")

def fetch_news(ticker: str) -> List[NewsItem]:
    """Fetch news items."""
    try:
        t = yf.Ticker(ticker)
        raw_news = t.news
        
        items = []
        for item in raw_news:
            # published is usually unix timestamp
            pub_ts = item.get('providerPublishTime', 0)
            
            # Generate a simple stable ID from uuid or link
            uuid = item.get('uuid', item.get('link'))
            if not uuid:
                import hashlib
                unique_string = f"{item.get('title')}-{pub_ts}"
                uuid = hashlib.md5(unique_string.encode('utf-8')).hexdigest()
            pub_date = datetime.fromtimestamp(pub_ts)
            
            items.append(NewsItem(
                id=uuid,
                title=item.get('title', ''),
                url=item.get('link', ''),
                published_at=pub_date,
                source=item.get('publisher', 'Yahoo'),
                summary=None, # Yahoo news standard payload usually has titles/links
                tickers=item.get('relatedTickers', [ticker]),
                provider="yahoo"
            ))
        return items
    except Exception as e:
        logger.error(f"Failed to fetch news for {ticker}: {e}")
        raise ProviderError(f"Yahoo news failed: {e}")
