# finfetch — Portfolio Plans

## 1) Purpose

Define portfolio-specific workflows for generating a weekly digest from a
user-defined ticker list (see `portfolio.yaml`).

Goals:
- Generate a **portfolio-only digest** (separate from the general market digest)
- Reuse existing fetch/export/digest plumbing where possible
- Produce Markdown + optional HTML output for easy reading

---

## 2) Inputs

- `portfolio.yaml` (local, not committed)
- `portfolio.example.yaml` (tracked template)

Proposed schema:

```yaml
portfolio:
  name: "My Portfolio"
  tickers:
    - AAPL
    - MSFT
```

---

## 3) Data Sources

- Yahoo Finance (fundamentals, prices, news)
- Finnhub (company news, market news)

---

## 4) Output Targets

Portfolio digest output (new):

- Markdown: `exports/portfolio/weekly_{YYYY}-W{WW}.md`
- Links CSV: `exports/portfolio/weekly_{YYYY}-W{WW}_news_links.csv`
- Prompt text: `exports/portfolio/weekly_{YYYY}-W{WW}_prompt.txt`
- Optional HTML: `exports/portfolio/weekly_{YYYY}-W{WW}.html`

---

## 5) Portfolio Digest Structure (Template A)

Sections:
1. Portfolio Snapshot
2. Sector Rotation
3. Top Themes
4. Portfolio News (per ticker)
5. Risks/Catalysts

Sentiment:
- Finnhub if available; fallback to weighted headline sentiment

---

## 6) Workflow

1) Ensure cache is populated:
   - `fetch fundamentals`, `fetch prices (5d/1d)`, `fetch news`
2) Generate portfolio digest from tickers in `portfolio.yaml`:
   - `finfetch digest --type weekly --portfolio --out ./exports`
3) Export Markdown + CSV
4) Convert to HTML (optional) via `scripts/market_digest_to_html.py`

---

## 7) Open Questions

Resolved:

- Output location: `exports/portfolio/`
- No position sizes/weights in the portfolio file (ticker list only)
- Single portfolio only
