.PHONY: digest-market fetch-financials export-ticker

TICKER ?= AAPL

digest-market:
	./bin/finfetch digest --type weekly --out ./exports

fetch-financials:
	./bin/finfetch fetch financials --ticker $(TICKER)

export-ticker:
	./bin/finfetch export --ticker $(TICKER) --out ./exports
