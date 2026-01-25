# finfetch — PLANS

## 1) Purpose

finfetch is a CLI tool designed for a long-term investor workflow:

- Fetch stock market data to analyze **fundamentals** and **narrative**
- Track **market sentiment** and major news themes to understand long-term trends
- Support writing blog posts:
  - current market condition (bull/bear, sector rotation, macro narrative)
  - individual stock deep dives (fundamentals + story + catalysts/risks)
  - portfolio status updates (holdings, thesis changes, key news)

finfetch’s job is to **collect, normalize, cache, and export** data so it can be used by:

- the CLI itself
- LLM workflows (reading exported files directly, bypassing the CLI if needed)

---

## 2) Data Sources (v0 → v1)

### Primary Source (v0)

- **Yahoo Finance Python library** (e.g., `yfinance`)
  - Price history (daily/weekly)
  - Basic company info / profile (as available)
  - Financial statements (as available)
  - Corporate actions (splits/dividends) where supported
  - News items (where available)

### Add-on Source (v1)

- **Finnhub API**
  - Additional news sources, richer metadata, sentiment features (as available)
  - More stable/structured endpoints vs scraped/aggregated feeds
  - Used as an optional enhancement layer

Source strategy:

- v0: implement Yahoo Finance first for fast iteration
- v1: add Finnhub as an optional provider and/or enrichment pipeline

---

## 3) Storage & Caching

### SQLite Cache (required)

Use SQLite as a local cache to speed up the CLI and reduce repeat fetches.
This is **not** a “source of truth” database. It exists to:

- de-duplicate
- avoid re-downloading unchanged data
- support incremental updates for daily/weekly runs

Cache design goals:

- keyed by (provider, ticker, data_type, time_range, params_hash)
- store raw responses and normalized records (when practical)
- TTL-based invalidation per data type (later milestone)

---

## 4) Outputs & Export Formats

finfetch must be able to export useful data into formats that are easy to use in:

- spreadsheets
- dashboards
- LLM workflows (direct file reads)

### Required export formats

- **JSON** (machine readable, structured)
- **CSV** (analysis-friendly for spreadsheets/pandas)
- **Markdown** (LLM-friendly and blog-friendly summaries)

Export goals:

- deterministic formatting and stable sorting
- consistent folder structure per ticker and per run date
- “summary” markdown files that combine narrative + key metrics + top news

### Digest helper scripts (repo-level)

These helpers support turning digest link CSVs into readable docs:

- `scripts/fetch_links.py` → generate Markdown digest scaffold with extracted text
- `scripts/market_digest_to_html.py` → convert Markdown to styled HTML

---

## 5) CLI Scope & Commands

### High-level command groups

- `finfetch fetch ...`  
  Fetch raw datasets (fundamentals, price history, news) and populate cache.

- `finfetch export ...`  
  Export cached datasets to JSON/CSV/MD for LLM/blog workflows.

- `finfetch digest ...`  
  Generate daily/weekly narrative-ready digests for blog writing.

### v0 CLI commands (MVP)

1. `finfetch fetch fundamentals --ticker TICKER`

   - Uses Yahoo Finance library
   - Stores normalized fundamentals + raw payload in SQLite

2. `finfetch fetch prices --ticker TICKER --period 5y --interval 1d`

   - Fetches historical prices
   - Normalizes OHLCV

3. `finfetch fetch news --ticker TICKER --days 7`

   - Fetches recent news (Yahoo first)
   - Normalizes items and de-dupes by stable ID

4. `finfetch fetch financials --ticker TICKER`

   - Fetches annual + quarterly income statement, balance sheet, and cashflow (Yahoo)
   - Stores in SQLite cache

5. `finfetch export --ticker TICKER --out ./exports`

   - Exports:
     - fundamentals.json / fundamentals.csv / fundamentals.md
     - prices.csv / prices.json (as needed)
     - news.json / news.csv / news.md
     - financial statements CSVs (income/balance/cashflow, annual + quarterly)

6. `finfetch digest --type weekly --out ./exports`
   - High-level orchestration:
     - loads tickers from `market.yaml` or `portfolio.yaml`
     - fetches missing cache data
     - generates the digest
7. `finfetch digest --type daily --date 2026-01-25 --out ./exports`
   - Daily market digest (tickers from `market.yaml`):
     - top themes (last 24h news)
     - notable headlines per ticker (last 24h)
     - sentiment notes
8. `finfetch fetch-digest weekly --tickers AAPL,CRDO --out ./exports`
   - Cache-only weekly digest (no fetching)
9. `finfetch fetch-digest daily --tickers AAPL,CRDO --date 2026-01-25 --out ./exports`
   - Cache-only daily digest (no fetching)

### v1 add-on commands

- `finfetch fetch news --provider finnhub ...`
- `finfetch fetch market-news --category general` (broad market news via Finnhub)
- `finfetch enrich news --sentiment ...`
- `finfetch digest market weekly` (broader market condition)

---

## 6) Data Model (Draft)

### Ticker

- symbol (string, uppercase)
- name (string, optional)
- sector / industry (optional)

### FundamentalsSnapshot

- updated_at (ISO8601)
- currency (optional)
- market_cap (optional)
- valuation metrics where available (optional)
- key ratios where available (optional)
- financial statement summaries where available (optional)
- raw_provider_payload (optional reference)

### PriceBar

- date (ISO8601 date)
- open, high, low, close
- adj_close (optional)
- volume

### NewsItem

- id (stable hash)
- title
- source
- url
- published_at (ISO8601)
- tickers (array)
- summary (optional)
- provider (yahoo / finnhub)
- raw (optional)

---

## 7) Output Contract (stdout)

All CLI commands return JSON on stdout by default.

Success:

```json
{ "ok": true, "data": {...}, "meta": { "version": 1 } }
```

Error:

```json
{
  "ok": false,
  "error": { "type": "...", "message": "...", "details": {} },
  "meta": { "version": 1 }
}
```

Notes:

- stdout is JSON only (unless `--format text` is explicitly supported later)
- logs/progress must go to stderr
- exit code 0 = success, non-zero = error

---

## 8) Export Folder Convention (Draft)

Default output folder: `./exports`

Example:

- `exports/`
  - `AAPL/`
    - `fundamentals.json`
    - `fundamentals.csv`
    - `fundamentals.md`
    - `AAPL_income_statement_annual.csv`
    - `AAPL_income_statement_quarterly.csv`
    - `AAPL_balance_sheet_annual.csv`
    - `AAPL_balance_sheet_quarterly.csv`
    - `AAPL_cashflow_annual.csv`
    - `AAPL_cashflow_quarterly.csv`
    - `prices_5y_1d.csv`
    - `news_7d.json`
    - `news_7d.md`
  - `CRDO/`
    - ...
  - `digests/`
    - `weekly_2026-W04.md`
    - `weekly_2026-W04_prompt.txt`
    - `daily_2026-01-25.md`
    - `daily_2026-01-25_prompt.txt`
  - `portfolio/`
    - `weekly_2026-W04.md`
    - `weekly_2026-W04_news_links.csv`
    - `weekly_2026-W04_prompt.txt`
    - `weekly_2026-W04.html`

Rules:

- filenames must be deterministic
- markdown must be clean for LLM ingestion (headings, bullet lists, short sections)

---

## 9) Milestones

M0 — Scaffolding [DONE]

- [x] CLI skeleton + rules enforced (JSON stdout, stderr logs)
- [x] SQLite cache module placeholder

M1 — Yahoo Finance v0 [DONE]

- [x] Implement `fetch fundamentals`, `fetch prices`, `fetch news` using Yahoo library
- [x] Store normalized + raw data in SQLite

M2 — Export Pipeline [DONE]

- [x] Implement `export` to JSON/CSV/MD
- [x] Establish stable folder conventions

M3 — Digest (Weekly/Daily) [DONE]

- [x] Implement cache-only digest generators and a high-level orchestrator

M4 — Finnhub Add-on [DONE]

- [x] Add Finnhub provider and enrichment options (config/env-based)
- [x] Optional sentiment features and broader market digest

---

## 10) Open Questions (defer; do not block v0)

Resolved preferences:

- Weekly post structure: Template A (market snapshot → sector rotation → top themes → headlines per ticker → risks/catalysts).
- Sentiment: Finnhub sentiment when available; fallback to weighted method if not.

---

## 11) Future Work (Proposed)

1) Portfolio-specific headings
   - Rename sections for portfolio digests (e.g., “Portfolio Snapshot” instead of “Market Snapshot”).

2) Finnhub news robustness
   - Add retries/backoff for Finnhub news.
   - Log when Finnhub returns empty results.

3) Fundamentals enrichment
   - Optional Finnhub financials fallback when Yahoo lacks revenue/FCF metrics.

4) HTML digest output
   - Add CLI flag to auto-render HTML after digest (optional).

5) Prompt customization
   - Add flags for prompt length or sections (e.g., include “Risks/Catalysts”).
