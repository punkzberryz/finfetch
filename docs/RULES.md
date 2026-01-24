# finfetch — RULES

These rules are **authoritative and non-optional**.
All contributors and agents (including Codex) MUST follow them.

---

## 1) CLI Contract (Hard Rules)

1. `stdout` MUST contain **machine-readable JSON only**.
2. Human-readable output (logs, progress, warnings) MUST go to `stderr`.
3. Exit code:
   - `0` → success
   - non-zero → error
4. Even on failure, `stdout` MUST return a valid JSON error object.
5. Output JSON schemas MUST be versioned via `meta.version`.

Breaking any of the above is considered a breaking change.

---

## 2) Output Shape (Mandatory)

### Success

All successful commands MUST follow this shape:

    {
      "ok": true,
      "data": { ... },
      "meta": {
        "version": 1
      }
    }

### Error

All errors MUST follow this shape:

    {
      "ok": false,
      "error": {
        "type": "ValidationError | NetworkError | RateLimitError | ProviderError | UnknownError",
        "message": "Human-readable summary",
        "details": { }
      },
      "meta": {
        "version": 1
      }
    }

Rules:

- No stack traces in stdout
- `error.type` MUST be stable and predictable
- Sensitive information MUST NOT appear in errors

---

## 3) Inputs & Validation

- All user input MUST be validated at the CLI boundary.
- Dates MUST use ISO8601 (`YYYY-MM-DD`).
- Tickers MUST be normalized to uppercase internally.
- Comma-separated lists MUST be supported where applicable.
- Invalid input MUST fail fast with `ValidationError`.

---

## 4) Providers & Networking

- All external API calls MUST use explicit timeouts.
- Transient failures MAY be retried with backoff.
- Provider-specific quirks MUST be normalized before export.
- Providers MUST be explicitly labeled (`provider = yahoo | finnhub`).

API keys:

- MUST come from environment variables or config files
- MUST NOT be passed as positional CLI arguments
- MUST NOT be logged

---

## 5) Caching Rules (SQLite)

SQLite is a **cache**, not a source of truth.

Rules:

- Cache entries MUST be keyed by:
  `(provider, ticker, data_type, time_range, params_hash)`
- Raw provider responses SHOULD be stored when practical.
- Normalized records MAY be stored for faster export.
- Cache invalidation SHOULD be TTL-based per data type.
- The CLI MUST still function correctly if the cache is empty.

---

## 6) Export Rules (Critical)

Exports are designed to be consumed by:

- spreadsheets
- scripts
- LLMs (without running the CLI)

### Required formats

- JSON
- CSV
- Markdown

### Export guarantees

- Filenames MUST be deterministic.
- Sorting MUST be stable.
- Exports MUST be reproducible for the same inputs.
- Markdown MUST be clean, structured, and LLM-friendly.

---

## 7) Export Folder Structure (Mandatory)

Default export root: `./exports`

Structure:

- `exports/`
  - `{TICKER}/`
    - `fundamentals.json`
    - `fundamentals.csv`
    - `fundamentals.md`
    - `prices_{period}_{interval}.csv`
    - `prices_{period}_{interval}.json`
    - `news_{days}d.json`
    - `news_{days}d.csv`
    - `news_{days}d.md`
  - `digests/`
    - `weekly_{YYYY}-W{WW}.md`
    - `weekly_{YYYY}-W{WW}_news_links.csv`

Rules:

- Do NOT invent new folder structures without updating PLANS.md.
- Markdown digests MUST include:
  - clear headings
  - bullet points
  - concise paragraphs
- No timestamps in filenames unless explicitly required.

---

## 8) Determinism & Reproducibility

- Sorting order MUST be explicit (e.g., date desc, source asc).
- Stable IDs MUST be used for de-duplication.
- The same inputs MUST produce the same outputs (excluding timestamps).

---

## 9) Scope Restrictions (Hard Limits)

finfetch MUST NOT:

- Execute trades or place orders
- Integrate with broker accounts
- Act as a real-time trading system
- Produce buy/sell recommendations

finfetch IS:

- a data ingestion tool
- a research and narrative support tool
- a long-term investing workflow assistant

---

## 10) Testing Rules

- Unit tests MUST NOT hit real external APIs.
- Provider calls MUST be mocked.
- Export tests MUST validate:
  - file existence
  - file format
  - deterministic ordering

---

## 11) Changes & Versioning

- Any breaking change to output shape or export structure MUST:
  1. Update `PLANS.md`
  2. Bump `meta.version`
  3. Be clearly documented

Silent breaking changes are not allowed.
