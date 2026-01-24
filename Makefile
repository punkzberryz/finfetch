.PHONY: help digest-market digest-portfolio fetch-missing-market fetch-missing-portfolio html-market html-portfolio

PYTHONPATH=finfetch/src
CLI=python -m finfetch.cli

help:
	@echo "Available targets:"
	@echo "  digest-market              Generate market digest (AAPL,MSFT example)"
	@echo "  digest-portfolio           Generate portfolio digest using portfolio.yaml"
	@echo "  fetch-missing-market       Market digest with fetch-missing"
	@echo "  fetch-missing-portfolio    Portfolio digest with fetch-missing"
	@echo "  html-market                Convert latest market digest markdown to HTML"
	@echo "  html-portfolio             Convert latest portfolio digest markdown to HTML"

# Update tickers in market.yaml (example in market.example.yaml)
MARKET_TICKERS=$(shell python - <<'PY' \
import yaml \
from pathlib import Path \
def load(path): \
    p=Path(path) \
    if not p.exists(): \
        return None \
    data=yaml.safe_load(p.read_text()) or {} \
    tickers=(data.get('market') or {}).get('tickers') or [] \
    return [t.strip().upper() for t in tickers if isinstance(t,str) and t.strip()] \
for path in ['market.yaml','market.example.yaml']: \
    t=load(path) \
    if t: \
        print(','.join(t)) \
        break \
PY \
)

# Derived paths
WEEK=$(shell python - <<'PY'
import datetime
now=datetime.date.today()
y,w,_=now.isocalendar()
print(f"{y}-W{w:02d}")
PY
)

MARKET_MD=exports/digests/weekly_$(WEEK).md
PORTFOLIO_MD=exports/portfolio/weekly_$(WEEK).md


digest-market:
	PYTHONPATH=$(PYTHONPATH) $(CLI) digest weekly --tickers $(MARKET_TICKERS) --out ./exports

fetch-missing-market:
	PYTHONPATH=$(PYTHONPATH) $(CLI) digest weekly --tickers $(MARKET_TICKERS) --out ./exports --fetch-missing


digest-portfolio:
	PYTHONPATH=$(PYTHONPATH) $(CLI) digest weekly --portfolio --out ./exports

fetch-missing-portfolio:
	PYTHONPATH=$(PYTHONPATH) $(CLI) digest weekly --portfolio --out ./exports --fetch-missing


html-market:
	python scripts/market_digest_to_html.py --input $(MARKET_MD) --out exports/digests/weekly_$(WEEK).html --title "Market Digest"

html-portfolio:
	python scripts/market_digest_to_html.py --input $(PORTFOLIO_MD) --out exports/portfolio/weekly_$(WEEK).html --title "Portfolio Digest"
