import datetime
import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "finfetch" / "src"
sys.path.insert(0, str(SRC))

from finfetch.providers import yahoo
from finfetch.cache.transcripts import TranscriptStore
from finfetch.export import transcript_export


TEST_URL = "https://finance.yahoo.com/quote/IREN/earnings/IREN-Q1-2026-earnings_call-380008.html"
SAMPLE_HTML = """
<html>
<head>
<script type="application/ld+json">
{
  "@context": "http://schema.org",
  "@type": "NewsArticle",
  "headline": "Iris Energy Limited (IREN) Q1 2026 Earnings Call Transcript",
  "datePublished": "2026-05-15T12:00:00Z",
  "articleBody": "Operator: Good day, and welcome to the conference call.\\nDaniel Roberts -- Co-Founder: Thanks for joining us today.\\nAnalyst: Can you talk about margins?\\nDaniel Roberts: Happy to discuss the details."
}
</script>
</head>
<body><p>Fallback body</p></body>
</html>
"""


class TestTranscriptParsing(unittest.TestCase):
    def test_parse_sample_transcript(self):
        transcript = yahoo.scrape_transcript(TEST_URL, html_override=SAMPLE_HTML)

        self.assertEqual(transcript.symbol, "IREN")
        self.assertEqual(transcript.company, "Iris Energy Limited")
        self.assertEqual(transcript.quarter, "Q1 2026")
        self.assertEqual(transcript.event_date, datetime.date(2026, 5, 15))
        self.assertIn("Operator", transcript.speakers)
        self.assertGreaterEqual(len(transcript.sections), 2)
        self.assertIn("Good day", transcript.full_text)

    def test_store_and_export(self):
        transcript = yahoo.scrape_transcript(TEST_URL, html_override=SAMPLE_HTML)

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TranscriptStore(db_path=str(Path(tmpdir) / "cache.db"))
            store.upsert(transcript)
            cached = store.get(TEST_URL)
            self.assertIsNotNone(cached)
            self.assertEqual(cached["symbol"], "IREN")

            paths = transcript_export.export_transcript(cached, out_root=tmpdir)
            self.assertTrue(Path(paths["json"]).exists())
            self.assertTrue(Path(paths["markdown"]).exists())

            exported = json.loads(Path(paths["json"]).read_text())
            self.assertEqual(exported["symbol"], "IREN")
            md_content = Path(paths["markdown"]).read_text()
            self.assertIn("Earnings Call Transcript", md_content)


if __name__ == "__main__":
    unittest.main()
