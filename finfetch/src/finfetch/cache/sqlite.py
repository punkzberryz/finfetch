import sqlite3
import json
import logging
from typing import Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class SQLiteCache:
    """
    Simple Key-Value cache backed by SQLite.
    Schema: cache(key TEXT PRIMARY KEY, data TEXT, created_at TEXT)
    """
    def __init__(self, db_path: str = "finfetch_cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache (
                        key TEXT PRIMARY KEY,
                        data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to init cache at {self.db_path}: {e}")

    def get(self, key: str) -> Optional[Any]:
        """Retrieve and parse JSON data from cache."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT data FROM cache WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
        return None

    def put(self, key: str, value: Any):
        """Store data as JSON string."""
        try:
            json_str = json.dumps(value)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO cache (key, data, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, json_str))
                conn.commit()
        except Exception as e:
            logger.error(f"Cache put failed for {key}: {e}")
