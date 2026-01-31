import json
import logging
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import yfinance as yf

from ..errors import ProviderError
from ..models.fundamentals import FundamentalsSnapshot
from ..models.news import NewsItem
from ..models.prices import PriceBar
from ..models.transcript import Transcript, TranscriptSection

logger = logging.getLogger(__name__)

_FINNHUB_NEWS_RE = re.compile(r"^https?://finnhub\.io/api/news\?id=")
_SPARSE_COL_THRESHOLD = 0.8
_FINANCIALS_KEY_MAP = {
    "Operating Revenue": "Total Revenue",
    "Selling General And Administrative": "Selling General And Administration",
}

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
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            resolved = page.url
            browser.close()
            if resolved and resolved != url:
                return resolved
    except Exception:
        return url
    return url

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
            
            url = item.get('link', '')
            url = _resolve_finnhub_link(url)

            items.append(NewsItem(
                id=uuid,
                title=item.get('title', ''),
                url=url,
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


def _df_to_records(df: Any) -> List[Dict[str, Any]]:
    if df is None or getattr(df, "empty", True):
        return []

    items: List[Dict[str, Any]] = []
    cols = []
    for c in df.columns:
        dt = None
        if hasattr(c, "to_pydatetime"):
            try:
                dt = c.to_pydatetime()
            except Exception:
                dt = None
        elif isinstance(c, datetime):
            dt = c
        elif isinstance(c, date):
            dt = datetime.combine(c, datetime.min.time())
        else:
            try:
                parsed = pd.to_datetime(c, errors="coerce")
                if not pd.isna(parsed):
                    dt = parsed.to_pydatetime()
            except Exception:
                dt = None
        label = dt.date().isoformat() if dt else str(c)
        sort_key = dt or datetime.min
        cols.append((sort_key, label, c))

    cols.sort(key=lambda x: (x[0], x[1]), reverse=True)

    for _, label, col in cols:
        record: Dict[str, Any] = {"date": label}
        series = df[col]
        for idx, val in series.items():
            key = str(idx)
            if pd.isna(val):
                record[key] = None
            else:
                try:
                    record[key] = float(val)
                except Exception:
                    record[key] = val
        items.append(record)

    return items


def _normalize_statement_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not records:
        return []

    normalized: List[Dict[str, Any]] = []
    for rec in records:
        out: Dict[str, Any] = {"date": rec.get("date")}
        for key, val in rec.items():
            if key == "date":
                continue
            canon = _FINANCIALS_KEY_MAP.get(key, key)
            if canon in out and out[canon] is not None:
                continue
            out[canon] = val
        normalized.append(out)

    # Union of keys across all records (excluding date)
    all_keys = set()
    for rec in normalized:
        all_keys.update(k for k in rec.keys() if k != "date")

    # Drop sparse columns
    keep_keys = set()
    total = len(normalized)
    for key in all_keys:
        missing = sum(1 for rec in normalized if rec.get(key) is None)
        if total == 0:
            continue
        if (missing / total) <= _SPARSE_COL_THRESHOLD:
            keep_keys.add(key)

    # Ensure consistent columns across records
    final_records: List[Dict[str, Any]] = []
    for rec in normalized:
        row = {"date": rec.get("date")}
        for key in keep_keys:
            row[key] = rec.get(key)
        final_records.append(row)

    # Drop rows that are mostly missing (likely unreliable periods)
    if keep_keys:
        filtered: List[Dict[str, Any]] = []
        total_keys = len(keep_keys)
        for row in final_records:
            missing = sum(1 for key in keep_keys if row.get(key) is None)
            if (missing / total_keys) <= _SPARSE_COL_THRESHOLD:
                filtered.append(row)
        return filtered

    return final_records


def fetch_financials(ticker: str) -> Dict[str, Any]:
    """Fetch annual and quarterly financial statements from Yahoo Finance."""
    try:
        t = yf.Ticker(ticker)

        income_annual = _normalize_statement_records(_df_to_records(t.financials))
        income_quarterly = _normalize_statement_records(_df_to_records(t.quarterly_financials))

        balance_annual = _normalize_statement_records(_df_to_records(t.balance_sheet))
        balance_quarterly = _normalize_statement_records(_df_to_records(t.quarterly_balance_sheet))

        cash_annual = _normalize_statement_records(_df_to_records(t.cashflow))
        cash_quarterly = _normalize_statement_records(_df_to_records(t.quarterly_cashflow))

        return {
            "symbol": ticker,
            "provider": "yahoo",
            "income_statement": {
                "annual": income_annual,
                "quarterly": income_quarterly,
            },
            "balance_sheet": {
                "annual": balance_annual,
                "quarterly": balance_quarterly,
            },
            "cashflow": {
                "annual": cash_annual,
                "quarterly": cash_quarterly,
            },
        }
    except Exception as e:
        logger.error(f"Failed to fetch financials for {ticker}: {e}")
        raise ProviderError(f"Yahoo financials failed: {e}")


_TRANSCRIPT_UA = "Mozilla/5.0 (finfetch transcript scraper)"


def _fetch_transcript_html(url: str) -> str:
    last_error: Optional[Exception] = None
    try:
        resp = requests.get(url, headers={"User-Agent": _TRANSCRIPT_UA}, timeout=15)
        if resp.status_code < 400:
            return resp.text
        last_error = ProviderError(f"Yahoo transcript fetch failed: HTTP {resp.status_code}")
    except requests.RequestException as exc:
        logger.error(f"Transcript fetch failed for {url}: {exc}")
        last_error = ProviderError(f"Yahoo transcript fetch failed: {exc}")

    # Playwright fallback for sites that block non-browser clients
    try:
        from playwright.sync_api import sync_playwright  # type: ignore

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
            content = page.content()
            browser.close()

        if response and response.status >= 400:
            raise ProviderError(f"Yahoo transcript fetch failed: HTTP {response.status}")
        if not content:
            raise ProviderError("Yahoo transcript fetch failed: empty page via Playwright")
        return content
    except ImportError:
        logger.error("Playwright not installed; run `playwright install chromium` to enable fallback.")
    except Exception as exc:  # pragma: no cover - network / runtime dependent
        logger.error(f"Playwright transcript fetch failed for {url}: {exc}")
        last_error = last_error or exc

    raise ProviderError(str(last_error) if last_error else "Yahoo transcript fetch failed")


def _extract_ld_json(html_text: str) -> Optional[Dict[str, Any]]:
    scripts = re.findall(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        html_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for raw in scripts:
        try:
            data = json.loads(raw.strip())
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if isinstance(item, dict) and item.get("articleBody"):
                return item
    return None


def _parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned).date()
    except Exception:
        return None


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except Exception:
        return None


def _parse_quarter(text: str, url: str) -> Optional[str]:
    for source in (text, url):
        match = re.search(r"(Q[1-4])[\s-]*(20\d{2})", source or "", flags=re.IGNORECASE)
        if match:
            quarter = f"{match.group(1).upper()} {match.group(2)}"
            return quarter
    return None


def _parse_symbol_company(headline: str, url: str) -> Dict[str, Optional[str]]:
    symbol = None
    company = None

    m = re.search(r"\(([^)]+)\)", headline or "")
    if m:
        symbol = m.group(1).strip().upper()
    m2 = re.match(r"(.+?)\s*\(", headline or "")
    if m2:
        company = m2.group(1).strip()

    if not symbol:
        m = re.search(r"/quote/([A-Za-z\.-]+)/", url or "")
        if m:
            symbol = m.group(1).upper()

    return {"symbol": symbol, "company": company}


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def _looks_like_speaker_header(text: str) -> bool:
    if not text:
        return False
    words = text.split()
    if len(words) == 0 or len(words) > 6:
        return False
    letters = "".join(words)
    return letters.isalpha()


def _parse_speaker_line(line: str) -> Optional[tuple]:
    if not line:
        return None
    raw = line.strip()
    if len(raw) > 120:
        return None

    if ":" in raw:
        head, rest = raw.split(":", 1)
        head = head.strip()
        role = None
        for sep in (" -- ", " - "):
            if sep in head:
                head, role = [p.strip() for p in head.split(sep, 1)]
                break
        if _looks_like_speaker_header(head):
            return head, role, rest.strip()

    if _looks_like_speaker_header(raw):
        return raw, None, None
    return None


def _parse_sections_from_body(body_text: str) -> Dict[str, Any]:
    lines = [ln.strip() for ln in body_text.splitlines() if ln.strip()]
    sections: List[Dict[str, str]] = []
    current_speaker = "Narrator"
    current_role = None
    buffer: List[str] = []

    def flush():
        if buffer:
            text_block = " ".join(buffer).strip()
            sections.append(
                {"speaker": current_speaker, "role": current_role, "text": text_block}
            )

    for line in lines:
        speaker_info = _parse_speaker_line(line)
        if speaker_info:
            flush()
            buffer = []
            current_speaker, current_role, remainder = speaker_info
            if remainder:
                buffer.append(remainder)
            continue
        buffer.append(line)

    flush()

    speakers: List[str] = []
    for section in sections:
        sp = section.get("speaker") or "Narrator"
        if sp not in speakers:
            speakers.append(sp)

    full_text = "\n\n".join(sec.get("text", "") for sec in sections if sec.get("text"))

    return {"sections": sections, "speakers": speakers, "full_text": full_text}


def _extract_body_from_html(html_text: str) -> Optional[str]:
    ld_json = _extract_ld_json(html_text)
    if ld_json and ld_json.get("articleBody"):
        return ld_json.get("articleBody")

    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if paragraphs:
        cleaned = [_strip_tags(p).strip() for p in paragraphs]
        return "\n".join([p for p in cleaned if p])
    return None


def scrape_transcript(url: str, html_override: Optional[str] = None) -> Transcript:
    """Scrape and normalize a Yahoo Finance earnings call transcript."""
    html_text = html_override if html_override is not None else _fetch_transcript_html(url)
    body_text = _extract_body_from_html(html_text or "")
    if not body_text:
        raise ProviderError("Yahoo transcript parse failed: no article body found.")

    ld_json = _extract_ld_json(html_text or "") or {}
    headline = ld_json.get("headline", "")

    meta = _parse_symbol_company(headline, url)
    event_date = _parse_iso_date(ld_json.get("datePublished"))
    quarter = _parse_quarter(headline, url)

    parsed_sections = _parse_sections_from_body(body_text)
    sections = [
        TranscriptSection(
            speaker=sec.get("speaker", "Narrator"),
            role=sec.get("role"),
            text=sec.get("text", ""),
        ).model_dump(mode="json")
        for sec in parsed_sections["sections"]
    ]

    transcript = Transcript(
        provider="yahoo",
        url=url,
        symbol=meta.get("symbol"),
        company=meta.get("company"),
        title=headline or None,
        quarter=quarter,
        event_date=event_date,
        published_at=_parse_iso_datetime(ld_json.get("datePublished")),
        speakers=parsed_sections["speakers"],
        sections=sections,  # type: ignore[arg-type]
        full_text=parsed_sections["full_text"],
        raw_html=html_text,
    )

    return transcript
