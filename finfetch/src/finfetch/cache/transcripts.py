import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from ..models.transcript import Transcript

logger = logging.getLogger(__name__)


class TranscriptStore:
    """Store normalized + raw transcripts in SQLite."""

    def __init__(self, db_path: str = "finfetch_cache.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS transcripts (
                        url TEXT PRIMARY KEY,
                        symbol TEXT,
                        company TEXT,
                        title TEXT,
                        quarter TEXT,
                        event_date TEXT,
                        published_at TEXT,
                        speakers TEXT,
                        sections TEXT,
                        full_text TEXT,
                        raw_html TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                conn.commit()
        except Exception as exc:
            logger.error(f"Failed to init transcript store at {self.db_path}: {exc}")

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored transcript by URL."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT symbol, company, title, quarter, event_date, published_at, speakers, sections, full_text, raw_html, url "
                    "FROM transcripts WHERE url = ?",
                    (url,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                (
                    symbol,
                    company,
                    title,
                    quarter,
                    event_date,
                    published_at,
                    speakers_json,
                    sections_json,
                    full_text,
                    raw_html,
                    stored_url,
                ) = row
                return {
                    "provider": "yahoo",
                    "url": stored_url,
                    "symbol": symbol,
                    "company": company,
                    "title": title,
                    "quarter": quarter,
                    "event_date": event_date,
                    "published_at": published_at,
                    "speakers": json.loads(speakers_json) if speakers_json else [],
                    "sections": json.loads(sections_json) if sections_json else [],
                    "full_text": full_text or "",
                    "raw_html": raw_html,
                }
        except Exception as exc:
            logger.warning(f"Transcript lookup failed for {url}: {exc}")
            return None

    def upsert(self, transcript: Transcript) -> None:
        """Insert or replace a transcript record."""
        payload = transcript.model_dump(mode="json", by_alias=True)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO transcripts (
                        url, symbol, company, title, quarter, event_date, published_at,
                        speakers, sections, full_text, raw_html, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        payload.get("url"),
                        payload.get("symbol"),
                        payload.get("company"),
                        payload.get("title"),
                        payload.get("quarter"),
                        payload.get("event_date"),
                        payload.get("published_at"),
                        json.dumps(payload.get("speakers", [])),
                        json.dumps(payload.get("sections", [])),
                        payload.get("full_text"),
                        payload.get("raw_html"),
                    ),
                )
                conn.commit()
        except Exception as exc:
            logger.error(f"Failed to store transcript for {payload.get('url')}: {exc}")
