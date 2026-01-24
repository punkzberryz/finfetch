.PHONY: help digest-market digest-portfolio fetch-missing-market fetch-missing-portfolio html-market html-portfolio

PYTHONPATH=finfetch/src
CLI=python -m finfetch.cli

help:
	@echo "Available targets:"
	@echo "  digest-market              Generate market digest using market.yaml"
	@echo "  digest-portfolio           Generate portfolio digest using portfolio.yaml"
	@echo "  fetch-missing-market       Market digest with fetch-missing"
	@echo "  fetch-missing-portfolio    Portfolio digest with fetch-missing"
	@echo "  html-market                Convert latest market digest markdown to HTML"
	@echo "  html-portfolio             Convert latest portfolio digest markdown to HTML"

# Update tickers in market.yaml
MARKET_YAML?=market.yaml
MARKET_TICKERS=$(shell python scripts/market_tickers.py --path $(MARKET_YAML))

# Derived paths
WEEK=$(shell python -c "import datetime; now=datetime.date.today(); y,w,_=now.isocalendar(); print(f'{y}-W{w:02d}')")

MARKET_MD=exports/digests/weekly_$(WEEK).md
PORTFOLIO_MD=exports/portfolio/weekly_$(WEEK).md


digest-market:
	@test -n "$(MARKET_TICKERS)" || (echo "No tickers found in $(MARKET_YAML)" >&2; exit 1)
	PYTHONPATH=$(PYTHONPATH) $(CLI) digest weekly --tickers $(MARKET_TICKERS) --out ./exports

fetch-missing-market:
	@test -n "$(MARKET_TICKERS)" || (echo "No tickers found in $(MARKET_YAML)" >&2; exit 1)
	PYTHONPATH=$(PYTHONPATH) $(CLI) digest weekly --tickers $(MARKET_TICKERS) --out ./exports --fetch-missing


digest-portfolio:
	PYTHONPATH=$(PYTHONPATH) $(CLI) digest weekly --portfolio --out ./exports

fetch-missing-portfolio:
	PYTHONPATH=$(PYTHONPATH) $(CLI) digest weekly --portfolio --out ./exports --fetch-missing


html-market:
	python scripts/market_digest_to_html.py --input $(MARKET_MD) --out exports/digests/weekly_$(WEEK).html --title "Market Digest"

html-portfolio:
	python scripts/market_digest_to_html.py --input $(PORTFOLIO_MD) --out exports/portfolio/weekly_$(WEEK).html --title "Portfolio Digest"
