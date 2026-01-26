.PHONY: digest-market digest-market-daily digest-portfolio-weekly fetch-financials export-ticker

TICKER ?= AAPL
DATE ?= $(shell date +%F)

digest-market:
	./bin/finfetch digest --type weekly --out ./exports
digest-market-daily:
	./bin/finfetch digest --type daily --date $(DATE) --out ./exports
digest-portfolio-weekly:
	./bin/finfetch digest --type weekly --portfolio --out ./exports

fetch-financials:
	./bin/finfetch fetch financials --ticker $(TICKER)

export-ticker:
	./bin/finfetch export --ticker $(TICKER) --out ./exports
