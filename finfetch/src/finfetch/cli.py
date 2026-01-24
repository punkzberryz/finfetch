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
from .export.paths import get_export_dir
from .export import json_export, csv_export, md_export
from .digest import weekly as weekly_digest
from pathlib import Path

# Configure logging at module level
configure_logging()
cache = SQLiteCache()

@click.group()
def cli():
    """finfetch: Financial data fetcher."""
    pass

# ... (omitted)

@cli.group()
def digest():
    """Generate digests."""
    pass

@digest.command()
@click.option("--tickers", required=True, help="Comma-separated tickers (e.g. AAPL,MSFT)")
@click.option("--out", default="./exports", help="Export root directory")
def weekly(tickers, out):
    """
    Generate a weekly digest for the given tickers.
    Reads from existing cache.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(',')]
    out_dir = Path(out) / "digests"
    
    report_path = weekly_digest.generate_weekly_digest(ticker_list, out_dir)
    
    _print_json({
        "digest_file": str(report_path),
        "tickers": ticker_list
    })


@cli.command()
def version():
    """Print version information."""
    data = {"version": "0.3.0", "status": "M2 Export"}
    _print_json(data)

@cli.group()
def fetch():
    """Fetch data from providers."""
    pass

@cli.command()
@click.option("--ticker", required=True, help="Stock ticker symbol")
@click.option("--out", default="./exports", help="Export root directory")
def export(ticker, out):
    """
    Export cached data to JSON/CSV/MD.
    
    Tries to find cached data for:
    - Fundamentals
    - News (latest)
    - Prices (1mo/1d, 5d/1d common periods for now, or just what's found if we scanned keys)
    """
    export_dir = get_export_dir(ticker, root=out)
    results = []
    
    # 1. Fundamentals
    key_fund = f"yahoo:fundamentals:{ticker}"
    data_fund = cache.get(key_fund)
    if data_fund:
        json_export.export_json(data_fund, export_dir / "fundamentals.json")
        csv_export.export_fundamentals_csv(data_fund, export_dir / "fundamentals.csv")
        md_export.export_fundamentals_md(data_fund, export_dir / "fundamentals.md")
        results.append("fundamentals")

    # 2. News
    key_news = f"yahoo:news:{ticker}:latest"
    data_news = cache.get(key_news)
    if data_news:
        json_export.export_json(data_news, export_dir / "news_latest.json")
        csv_export.export_news_csv(data_news, export_dir / "news_latest.csv")
        md_export.export_news_md(data_news, export_dir / "news_latest.md")
        results.append("news")
        
    # 3. Prices - Check common intervals (Hack for v0 until we have better key scanning)
    price_configs = [("1mo", "1d"), ("5d", "1d"), ("1y", "1wk")]
    for p, i in price_configs:
        key_price = f"yahoo:prices:{ticker}:{p}:{i}"
        data_price = cache.get(key_price)
        if data_price:
            fname = f"prices_{p}_{i}"
            json_export.export_json(data_price, export_dir / f"{fname}.json")
            csv_export.export_prices_csv(data_price, export_dir / f"{fname}.csv")
            results.append(fname)
            
    _print_json({
        "exported": results,
        "directory": str(export_dir)
    })


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
