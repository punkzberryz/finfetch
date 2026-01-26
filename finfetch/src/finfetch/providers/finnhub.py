import requests
import logging
import datetime
import re
import os
from typing import List, Optional
from ..errors import ProviderError
from ..models.news import NewsItem
from ..config import get_finnhub_key

logger = logging.getLogger(__name__)

BASE_URL = "https://finnhub.io/api/v1"

_FINNHUB_NEWS_RE = re.compile(r"^https?://finnhub\.io/api/news\?id=")

def _extract_canonical_url(html_text: str) -> Optional[str]:
    for pat in (
        r'rel=\"canonical\" href=\"([^\"]+)\"',
        r'property=\"og:url\" content=\"([^\"]+)\"',
        r'name=\"og:url\" content=\"([^\"]+)\"'
    ):
        m = re.search(pat, html_text)
        if m:
            return m.group(1).strip()
    return None

def _resolve_finnhub_link(url: str) -> str:
    if not url or not _FINNHUB_NEWS_RE.match(url):
        return url
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=False,
            timeout=10
        )
        if resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get("Location")
            if loc:
                return loc
        if resp.status_code == 200:
            resolved = _extract_canonical_url(resp.text)
            return resolved or url
    except Exception:
        pass
    # Headless fallback for finnhub redirect pages
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        timeout_ms = int(os.getenv("FINFETCH_PLAYWRIGHT_TIMEOUT_MS", "5000"))
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, timeout=timeout_ms)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            resolved = page.url
            browser.close()
            if resolved and resolved != url:
                return resolved
    except Exception:
        return url
    return url

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

            url = item.get('url', '')
            url = _resolve_finnhub_link(url)

            items.append(NewsItem(
                id=news_id,
                title=item.get('headline', ''),
                url=url,
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

def fetch_market_news(category: str = "general", min_id: int = 0) -> List[NewsItem]:
    """
    Fetch broad market news from Finnhub.
    Reference: https://github.com/Finnhub-Stock-API/finnhub-python
    """
    api_key = get_finnhub_key()
    if not api_key:
        raise ProviderError(
            "FINNHUB_API_KEY is missing or invalid. "
            "Please add it to your .env file."
        )

    url = f"{BASE_URL}/news"
    params = {
        "category": category,
        "minId": min_id,
        "token": api_key
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        items = []
        for item in data:
            ts = item.get("datetime", 0)
            pub_date = datetime.datetime.fromtimestamp(ts)
            news_id = str(item.get("id", ""))
            if not news_id:
                import hashlib
                s = f"{item.get('headline')}-{ts}"
                news_id = hashlib.md5(s.encode()).hexdigest()

            items.append(NewsItem(
                id=news_id,
                title=item.get("headline", ""),
                url=item.get("url", ""),
                published_at=pub_date,
                source=item.get("source", "Finnhub"),
                summary=item.get("summary"),
                tickers=[],
                provider="finnhub"
            ))

        return items
    except requests.RequestException as e:
        logger.error(f"Finnhub market news request failed: {e}")
        raise ProviderError(f"Finnhub market news failed: {e}")
    except Exception as e:
        logger.error(f"Finnhub market news processing failed: {e}")
        raise ProviderError(f"Finnhub market news error: {e}")
