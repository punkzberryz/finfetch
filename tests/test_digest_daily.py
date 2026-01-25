import datetime
import tempfile
import unittest
from pathlib import Path
import sys
import csv

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "finfetch" / "src"
sys.path.insert(0, str(SRC))

from finfetch.cache.sqlite import SQLiteCache
from finfetch.digest import daily


def _seed_daily_cache(cache: SQLiteCache, ticker: str, day: datetime.date):
    on_day = datetime.datetime.combine(day, datetime.time(10, 0))
    within_24h = datetime.datetime.combine(day - datetime.timedelta(days=1), datetime.time(23, 59, 59))
    off_day = datetime.datetime.combine(day - datetime.timedelta(days=1), datetime.time(23, 59, 58))

    cache.put(
        f"yahoo:fundamentals:{ticker}",
        {
            "symbol": ticker,
            "name": "Acme Corp",
            "sector": "Technology",
            "industry": "Software",
        },
    )

    cache.put(
        f"yahoo:prices:{ticker}:5d:1d",
        [
            {"close": 100.0},
            {"close": 105.0},
        ],
    )

    cache.put(
        f"yahoo:news:{ticker}:latest",
        [
            {
                "id": "n1",
                "title": "Acme announces new product",
                "url": "https://example.com/on-day",
                "source": "Example News",
                "published_at": on_day.isoformat(),
                "provider": "yahoo",
            },
            {
                "id": "n1b",
                "title": "Acme late-day update",
                "url": "https://example.com/within-24h",
                "source": "Example News",
                "published_at": within_24h.isoformat(),
                "provider": "yahoo",
            },
            {
                "id": "n2",
                "title": "Acme quarterly results from prior day",
                "url": "https://example.com/off-day",
                "source": "Example News",
                "published_at": off_day.isoformat(),
                "provider": "yahoo",
            },
        ],
    )

    cache.put(
        "finnhub:market_news:general:0",
        [
            {
                "id": "m1",
                "title": "Markets rise on policy shift",
                "url": "https://example.com/market-on-day",
                "source": "Example Wire",
                "published_at": on_day.isoformat(),
                "provider": "finnhub",
            },
            {
                "id": "m1b",
                "title": "Markets recover late yesterday",
                "url": "https://example.com/market-within-24h",
                "source": "Example Wire",
                "published_at": within_24h.isoformat(),
                "provider": "finnhub",
            },
            {
                "id": "m2",
                "title": "Markets dip in late trading",
                "url": "https://example.com/market-off-day",
                "source": "Example Wire",
                "published_at": off_day.isoformat(),
                "provider": "finnhub",
            },
        ],
    )


class TestDailyDigest(unittest.TestCase):
    def test_daily_digest_filters_news_by_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            day = datetime.date(2026, 1, 25)
            db_path = str(Path(tmpdir) / "cache.db")
            out_dir = Path(tmpdir) / "exports" / "digests"

            daily.cache = SQLiteCache(db_path=db_path)
            _seed_daily_cache(daily.cache, "AAA", day)

            report_path = daily.generate_daily_digest(["AAA"], out_dir, digest_date=day)
            content = Path(report_path).read_text()
            csv_path = Path(str(report_path).replace(".md", "_news_links.csv"))
            with open(csv_path, newline="") as f:
                rows = list(csv.DictReader(f))

            self.assertIn("Acme announces new product", content)
            self.assertNotIn("prior day", content)
            self.assertTrue(any(r["url"] == "https://example.com/on-day" for r in rows))
            self.assertTrue(any(r["url"] == "https://example.com/within-24h" for r in rows))
            self.assertFalse(any(r["url"] == "https://example.com/off-day" for r in rows))
            self.assertTrue(any(r["url"] == "https://example.com/market-on-day" for r in rows))
            self.assertTrue(any(r["url"] == "https://example.com/market-within-24h" for r in rows))
            self.assertFalse(any(r["url"] == "https://example.com/market-off-day" for r in rows))


if __name__ == "__main__":
    unittest.main()
