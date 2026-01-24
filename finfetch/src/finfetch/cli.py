import sys
import json
import click
import hashlib
from .errors import format_error, FinFetchError
from .logging import configure_logging
from .models.fundamentals import FundamentalsSnapshot
from .models.prices import PriceBar
from .models.news import NewsItem
from .providers import yahoo
from .cache.sqlite import SQLiteCache

# Configure logging at module level
configure_logging()
cache = SQLiteCache()

@click.group()
def cli():
    """finfetch: Financial data fetcher."""
    pass

@cli.command()
def version():
    """Print version information."""
    data = {"version": "0.2.0", "status": "M1 Yahoo"}
    _print_json(data)

@cli.group()
def fetch():
    """Fetch data from providers."""
    pass

@fetch.command()
@click.option("--ticker", required=True, help="Stock ticker symbol")
@click.option("--force", is_flag=True, help="Bypass cache")
def fundamentals(ticker, force):
    """Fetch company fundamentals."""
    key = f"yahoo:fundamentals:{ticker}"
    
    if not force:
        cached = cache.get(key)
        if cached:
            _print_json(cached, cached=True)
            return

    data = yahoo.fetch_fundamentals(ticker)
    
    # Cache the dict representation
    as_dict = data.model_dump(mode='json', by_alias=True)
    cache.put(key, as_dict)
    
    _print_json(as_dict, cached=False)

@fetch.command()
@click.option("--ticker", required=True, help="Stock ticker symbol")
@click.option("--period", default="1mo", help="Data period (1d, 5d, 1mo, 1y, etc)")
@click.option("--interval", default="1d", help="Data interval (1m, 1h, 1d, 1wk)")
@click.option("--force", is_flag=True, help="Bypass cache")
def prices(ticker, period, interval, force):
    """Fetch price history."""
    # Key includes args
    key = f"yahoo:prices:{ticker}:{period}:{interval}"
    
    if not force:
        cached = cache.get(key)
        if cached:
            _print_json(cached, cached=True)
            return
            
    bars = yahoo.fetch_prices(ticker, period, interval)
    as_dict = [b.model_dump(mode='json') for b in bars]
    
    cache.put(key, as_dict)
    _print_json(as_dict, cached=False)

@fetch.command()
@click.option("--ticker", required=True, help="Stock ticker symbol")
@click.option("--force", is_flag=True, help="Bypass cache")
def news(ticker, force):
    """Fetch recent news."""
    # News is volatile; simplistic unique key doesn't work well for "latest"
    # We might want to cache with a short TTL or just by day.
    # For M1, we'll cache 'latest' but user should use --force to refresh.
    key = f"yahoo:news:{ticker}:latest"
    
    if not force:
        cached = cache.get(key)
        if cached:
            _print_json(cached, cached=True)
            return

    items = yahoo.fetch_news(ticker)
    as_dict = [i.model_dump(mode='json') for i in items]
    
    cache.put(key, as_dict)
    _print_json(as_dict, cached=False)


def _print_json(data, cached=False):
    """Helper to print standard JSON envelope."""
    payload = {
        "ok": True,
        "data": data,
        "meta": {
            "version": 1,
            "cached": cached
        }
    }
    click.echo(json.dumps(payload, indent=2))


def main():
    """Entry point for the CLI."""
    try:
        cli(standalone_mode=False)
    except Exception as e:
        if isinstance(e, click.exceptions.Exit):
             sys.exit(e.exit_code)
        if isinstance(e, click.exceptions.Abort):
             sys.exit(130)
        
        # Click usage errors (missing args) raise UsageError
        # convert them to JSON
        if isinstance(e, click.exceptions.UsageError):
             print(format_error(e)) # We might want a custom type for Usage
             sys.exit(1)

        print(format_error(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
