import requests
import logging
import datetime
from typing import List
from ..errors import ProviderError
from ..models.news import NewsItem
from ..config import get_finnhub_key

logger = logging.getLogger(__name__)

BASE_URL = "https://finnhub.io/api/v1"

def fetch_company_news(ticker: str, start: datetime.date, end: datetime.date) -> List[NewsItem]:
    """
    Fetch company news from Finnhub (Free Tier compliant).
    Reference: https://finnhub.io/docs/api/company-news
    """
    api_key = get_finnhub_key()
    if not api_key:
        raise ProviderError(
            "FINNHUB_API_KEY is missing or invalid. "
            "Please add it to your .env file."
        )

    url = f"{BASE_URL}/company-news"
    params = {
        "symbol": ticker,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "token": api_key
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        items = []
        for item in data:
            # Finnhub item: { 
            #   "category": "company", 
            #   "datetime": 1569550360, 
            #   "headline": "...", 
            #   "id": 1234, 
            #   "image": "...", 
            #   "related": "AAPL", 
            #   "source": "...", 
            #   "summary": "...", 
            #   "url": "..." 
            # }
            
            ts = item.get('datetime', 0)
            pub_date = datetime.datetime.fromtimestamp(ts)
            
            # ID is usually integer, convert to str
            news_id = str(item.get('id', ''))
            if not news_id:
                # Fallback checksum
                import hashlib
                s = f"{item.get('headline')}-{ts}"
                news_id = hashlib.md5(s.encode()).hexdigest()

            items.append(NewsItem(
                id=news_id,
                title=item.get('headline', ''),
                url=item.get('url', ''),
                published_at=pub_date,
                source=item.get('source', 'Finnhub'),
                summary=item.get('summary'),
                tickers=[ticker],
                provider="finnhub"
            ))
            
        return items
        
    except requests.RequestException as e:
        logger.error(f"Finnhub request failed: {e}")
        raise ProviderError(f"Finnhub fetch failed: {e}")
    except Exception as e:
        logger.error(f"Finnhub processing failed: {e}")
        raise ProviderError(f"Finnhub error: {e}")
