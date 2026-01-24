# finfetch

finfetch is a CLI tool for fetching financial market data to support
long-term investing research, market sentiment analysis, and blog workflows.

See:

- `AGENTS.md` for agent instructions
- `docs/PLANS.md` for project goals
- `docs/RULES.md` for non-negotiable constraints

## Notable Commands

- `finfetch fetch market-news --category general` (Finnhub broad market news)
- `finfetch digest weekly --tickers AAPL,MSFT --out ./exports` (weekly digest)

## Makefile

Use `market.yaml` (see `market.example.yaml`) to define market tickers, then run:

```
make digest-market
```

## Digest Helpers

These helpers live in `scripts/` and are used to turn digest link CSVs into a
readable Markdown + HTML view:

```
python scripts/fetch_links.py --input exports/digests/weekly_YYYY-WWW_news_links.csv --out /tmp/market_digest.md --cache-dir /tmp/link_cache
python scripts/market_digest_to_html.py --input /tmp/market_digest.md --out /tmp/market_digest.html --title "Market Digest"
```

## Skills

A packaged Codex skill is included at:

- `docs/skills/digest-from-links.skill`

Install notes live in `docs/skills/INSTALL.md`.
