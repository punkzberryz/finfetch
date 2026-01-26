# finfetch — CLI RULES

Authoritative and non-optional for CLI work.

---

## 1) CLI Output Contract (Hard Rules)

- `stdout` MUST be **machine-readable JSON only**; all logs/progress/warnings go to `stderr`.
- Exit code `0` = success; non-zero = error.
- Even on failure, `stdout` MUST be valid JSON.
- Output schemas MUST be versioned via `meta.version`.
- Breaking any of the above is a breaking change.

Output shapes and detailed schemas are defined in `docs/SCHEMAS.md`.

---

## 2) Inputs & Validation

- Validate all user input at the CLI boundary.
- Dates: ISO8601 (`YYYY-MM-DD`).
- Tickers: normalized to uppercase internally.
- Comma-separated lists supported where applicable.
- Invalid input MUST fail fast with `ValidationError`.
- High-level digest orchestration loads tickers from YAML (`market.yaml` or `portfolio.yaml`), not CLI args.

---

## 3) Providers & Networking

- External API calls MUST use explicit timeouts; transient failures MAY retry with backoff.
- Provider quirks MUST be normalized before export.
- Providers MUST be labeled (`provider = yahoo | finnhub`).
- API keys MUST come from env vars or config files, MUST NOT be positional args, and MUST NOT be logged.

---

## 4) Caching (SQLite)

SQLite is a **cache**, not a source of truth.

- Cache keys MUST include: `(provider, ticker, data_type, time_range, params_hash)`
- Raw provider responses SHOULD be stored when practical.
- Normalized records MAY be stored for faster export.
- Cache invalidation SHOULD be TTL-based per data type.
- CLI MUST function correctly with an empty cache.
- Financial statement normalization MUST be deterministic (stable columns, sparse rows dropped).

---

## 5) Orchestration (Digest)

- High-level digest MUST: read tickers from YAML, fetch only missing cache data, then call cache-only digest generation.
- Cache-only digest commands (e.g., `fetch-digest`) MUST NOT fetch data.

---

## 6) Exports (Critical)

Required formats: JSON, CSV, Markdown.

Guarantees:

- Filenames MUST be deterministic.
- Sorting MUST be stable and explicit.
- Same inputs MUST produce same outputs (excluding timestamps).
- Stable IDs MUST be used for de-duplication.
- Markdown MUST be clean, structured, and LLM-friendly.

Default export root: `./exports`

    exports/
      {TICKER}/
        fundamentals.json
        fundamentals.csv
        fundamentals.md
        {TICKER}_income_statement_annual.csv
        {TICKER}_income_statement_quarterly.csv
        {TICKER}_balance_sheet_annual.csv
        {TICKER}_balance_sheet_quarterly.csv
        {TICKER}_cashflow_annual.csv
        {TICKER}_cashflow_quarterly.csv
        prices_{period}_{interval}.csv
        prices_{period}_{interval}.json
        news_{days}d.json
        news_{days}d.csv
        news_{days}d.md
      digests/
        weekly_{YYYY}-W{WW}.md
        weekly_{YYYY}-W{WW}.json
        weekly_{YYYY}-W{WW}_news_links.csv
        weekly_{YYYY}-W{WW}_prompt.txt
        daily_{YYYY}-MM-DD.md
        daily_{YYYY}-MM-DD.json
        daily_{YYYY}-MM-DD_news_links.csv
        daily_{YYYY}-MM-DD_prompt.txt
      portfolio/
        weekly_{YYYY}-W{WW}.md
        weekly_{YYYY}-W{WW}.json
        weekly_{YYYY}-W{WW}_news_links.csv
        weekly_{YYYY}-W{WW}_prompt.txt

Rules:

- Do NOT invent new folder structures without updating `PLANS.md`.
- Markdown digests MUST include clear headings, bullet points, and concise paragraphs.
- No timestamps in filenames unless explicitly required.
