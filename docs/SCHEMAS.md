# finfetch — SCHEMAS

This document defines the authoritative JSON output shapes for the CLI.

---

## 1) Output Envelope (Required)

All CLI responses MUST use one of the following envelopes.

### Success

    {
      "ok": true,
      "data": { ... },
      "meta": { "version": 1 }
    }

### Error

    {
      "ok": false,
      "error": {
        "type": "ValidationError | NetworkError | RateLimitError | ProviderError | UnknownError",
        "message": "Human-readable summary",
        "details": { }
      },
      "meta": { "version": 1 }
    }

Rules:

- No stack traces in `stdout`
- `error.type` MUST be stable and predictable
- Sensitive information MUST NOT appear in errors

---

## 2) Error Types (Stable)

`error.type` MUST be one of:

- `ValidationError`
- `NetworkError`
- `RateLimitError`
- `ProviderError`
- `UnknownError`

---

## 3) Versioning

- `meta.version` MUST be present and integer.
- Schema changes MUST increment `meta.version`.
- Backwards-incompatible changes require updating `docs/PLANS.md`.

---

## 4) Digest JSON Files (exports/digests, exports/portfolio)

Digest JSON files are written alongside Markdown digests with deterministic filenames.

### Daily Digest JSON

    {
      "type": "daily",
      "date": "YYYY-MM-DD",
      "title": "# Daily Market Digest: ...",
      "tickers": ["AAPL", "MSFT"],
      "include_market_news": true,
      "market_snapshot": {
        "breadth": { "up": 3, "down": 2 },
        "average_change": 0.42,
        "best": { "ticker": "AAPL", "change": 1.2 },
        "worst": { "ticker": "TSLA", "change": -2.1 }
      },
      "sector_rotation": [{ "sector": "Tech", "average_change": 0.8 }],
      "top_themes": [{ "theme": "earnings", "count": 4 }],
      "market_news": [
        { "title": "...", "source": "...", "url": "...", "published_at": "...", "provider": "finnhub" }
      ],
      "ticker_highlights": [
        {
          "ticker": "AAPL",
          "name": "Apple Inc.",
          "sector": "Technology",
          "industry": "Consumer Electronics",
          "change": 0.5,
          "start_price": 190.1,
          "end_price": 191.0,
          "sentiment": { "source": "finnhub|weighted", "label": "Neutral", "score": 0.1 },
          "headlines": [
            { "title": "...", "source": "...", "url": "...", "published_at": "...", "provider": "yahoo" }
          ],
          "risks_catalysts": [{ "label": "Risk|Catalyst|Neutral", "title": "..." }]
        }
      ],
      "news_links": [
        { "scope": "ticker|market", "ticker": "AAPL", "source": "...", "title": "...", "url": "...", "published_at": "...", "provider": "..." }
      ]
    }

### Weekly Digest JSON

Same shape as Daily Digest JSON, plus:

    {
      "week": "YYYY-WWW"
    }

---

## 5) Transcript Scrape Output

Command: `finfetch scrape transcript --url <Yahoo transcript URL>`

`stdout` envelope:

    {
      "ok": true,
      "data": {
        "transcript": {
          "provider": "yahoo",
          "url": "...",
          "symbol": "IREN",
          "company": "Iris Energy Limited",
          "title": "Iris Energy Limited (IREN) Q1 2026 Earnings Call Transcript",
          "quarter": "Q1 2026",
          "event_date": "2026-05-15",
          "published_at": "2026-05-15T12:00:00+00:00",
          "speakers": ["Operator", "Daniel Roberts", "Analyst"],
          "sections": [{ "speaker": "Operator", "role": null, "text": "..." }],
          "full_text": "...",
          "raw_html": "<html>...</html>"
        },
        "exports": {
          "json": "./exports/transcripts/IREN/2026-05-15-q1-2026-380008.json",
          "markdown": "./exports/transcripts/IREN/2026-05-15-q1-2026-380008.md"
        }
      },
      "meta": { "version": 1, "cached": false }
    }

Notes:

- Markdown and JSON export filenames are deterministic: `{event_date}-{quarter|title_slug}-{id}.(json|md)`.
- `raw_html` is stored for debugging; downstream exports may ignore it.
