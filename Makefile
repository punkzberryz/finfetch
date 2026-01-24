.PHONY: digest-market

PYTHON ?= python
PYTHONPATH ?= finfetch/src

MARKET_TICKERS := $(shell $(PYTHON) scripts/market_tickers.py --path market.yaml)

digest-market:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m finfetch digest weekly --tickers $(MARKET_TICKERS) --out ./exports
