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
