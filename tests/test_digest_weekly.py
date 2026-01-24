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
from finfetch.digest import weekly


def _seed_basic_cache(cache: SQLiteCache, ticker: str, with_finnhub_sentiment: bool):
    now = datetime.datetime.now()

    cache.put(
        f"yahoo:fundamentals:{ticker}",
        {
            "symbol": ticker,
            "name": "Acme Corp",
            "sector": "Technology",
            "industry": "Software",
            "currency": "USD",
            "market_cap": 1500000000,
            "totalRevenue": 2500000000,
            "ebitda": 500000000,
            "netIncomeToCommon": 200000000,
            "trailingEps": 2.5,
            "freeCashflow": 300000000,
            "sharesOutstanding": 100000000,
            "revenueGrowth": 0.18,
            "earningsGrowth": 0.22,
            "debtToEquity": 0.35
        },
    )

    cache.put(
        f"yahoo:prices:{ticker}:5d:1d",
        [
            {"close": 100.0},
            {"close": 110.0}
        ],
    )

    cache.put(
        f"yahoo:news:{ticker}:latest",
        [
            {
                "id": "n1",
                "title": "Acme beats estimates on strong growth",
                "url": "https://example.com/1",
                "source": "Example News",
                "published_at": now.isoformat(),
                "provider": "yahoo"
            }
        ],
    )

    if with_finnhub_sentiment:
        cache.put(
            f"finnhub:sentiment:{ticker}:latest",
            {"label": "Positive", "score": 0.7}
        )

def _seed_market_news(cache: SQLiteCache):
    now = datetime.datetime.now()
    cache.put(
        "finnhub:market_news:general:0",
        [
            {
                "id": "m1",
                "title": "Market rallies on cooling inflation",
                "url": "https://example.com/market-1",
                "source": "Example Wire",
                "published_at": now.isoformat(),
                "provider": "finnhub"
            }
        ],
    )


class TestWeeklyDigest(unittest.TestCase):
    def test_weekly_digest_weighted_sentiment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "cache.db")
            out_dir = Path(tmpdir) / "exports" / "digests"

            weekly.cache = SQLiteCache(db_path=db_path)
            _seed_basic_cache(weekly.cache, "AAA", with_finnhub_sentiment=False)
            _seed_market_news(weekly.cache)

            report_path = weekly.generate_weekly_digest(["AAA"], out_dir)
            content = Path(report_path).read_text()
            csv_path = Path(str(report_path).replace(".md", "_news_links.csv"))
            prompt_path = Path(str(report_path).replace(".md", "_prompt.txt"))
            self.assertTrue(csv_path.exists())
            self.assertTrue(prompt_path.exists())
            with open(csv_path, newline="") as f:
                rows = list(csv.DictReader(f))

            self.assertIn("# Weekly Market Digest:", content)
            self.assertIn("## Market Snapshot", content)
            self.assertIn("## Sector Rotation", content)
            self.assertIn("## Top Themes", content)
            self.assertIn("## Market News", content)
            self.assertIn("## Ticker Highlights", content)
            self.assertIn("Sentiment: Positive (weighted", content)
            self.assertIn("Fundamentals (Core):", content)
            self.assertIn("Fundamentals (Growth):", content)
            self.assertIn("Debt/Equity:", content)
            self.assertTrue(any(r["scope"] == "market" for r in rows))
            self.assertTrue(any(r["scope"] == "ticker" for r in rows))

    def test_weekly_digest_finnhub_sentiment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "cache.db")
            out_dir = Path(tmpdir) / "exports" / "digests"

            weekly.cache = SQLiteCache(db_path=db_path)
            _seed_basic_cache(weekly.cache, "BBB", with_finnhub_sentiment=True)

            report_path = weekly.generate_weekly_digest(["BBB"], out_dir)
            content = Path(report_path).read_text()

            self.assertIn("Sentiment: Positive (Finnhub, score 0.70)", content)


if __name__ == "__main__":
    unittest.main()
