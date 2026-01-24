import sys
import json
import click
import hashlib
from .errors import format_error, FinFetchError
from .logging import configure_logging
from .models.fundamentals import FundamentalsSnapshot
from .models.prices import PriceBar
from .models.news import NewsItem
from .providers import yahoo, finnhub
from datetime import date, timedelta
from .cache.sqlite import SQLiteCache
from .export.paths import get_export_dir
from .export import json_export, csv_export, md_export
from .digest import weekly as weekly_digest
from .portfolio import load_portfolio
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
@click.option("--tickers", required=False, help="Comma-separated tickers (e.g. AAPL,MSFT)")
@click.option("--out", default="./exports", help="Export root directory")
@click.option("--fetch-missing", is_flag=True, help="Fetch missing cache data before digest")
@click.option("--portfolio", is_flag=True, help="Use tickers from portfolio.yaml")
def weekly(tickers, out, fetch_missing, portfolio):
    """
    Generate a weekly digest for the given tickers.
    Reads from existing cache.
    """
    if portfolio:
        portfolio_data = load_portfolio()
        ticker_list = portfolio_data["tickers"]
        title = f"# Portfolio Digest: {portfolio_data['name']} ({date.today().isocalendar()[0]}-W{date.today().isocalendar()[1]:02d})"
        out_dir = Path(out) / "portfolio"
        include_market_news = False
    else:
        if not tickers:
            raise click.BadParameter("tickers is required unless --portfolio is set.")
        ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
        if not ticker_list:
            raise click.BadParameter("tickers must include at least one symbol.")
        title = None
        out_dir = Path(out) / "digests"
        include_market_news = True

    if fetch_missing:
        for ticker in ticker_list:
            key_fund = f"yahoo:fundamentals:{ticker}"
            if not cache.get(key_fund):
                data = yahoo.fetch_fundamentals(ticker)
                cache.put(key_fund, data.model_dump(mode="json", by_alias=True))

            key_price = f"yahoo:prices:{ticker}:5d:1d"
            if not cache.get(key_price):
                bars = yahoo.fetch_prices(ticker, "5d", "1d")
                cache.put(key_price, [b.model_dump(mode="json") for b in bars])

            key_news = f"yahoo:news:{ticker}:latest"
            if not cache.get(key_news):
                items = yahoo.fetch_news(ticker)
                cache.put(key_news, [i.model_dump(mode="json") for i in items])

            key_finnhub = f"finnhub:news:{ticker}:latest"
            if not cache.get(key_finnhub):
                try:
                    end_d = date.today()
                    start_d = end_d - timedelta(days=7)
                    items = finnhub.fetch_company_news(ticker, start_d, end_d)
                    cache.put(key_finnhub, [i.model_dump(mode="json") for i in items])
                except FinFetchError:
                    pass
                except Exception:
                    pass

    report_path = weekly_digest.generate_weekly_digest(
        ticker_list,
        out_dir,
        title=title,
        include_market_news=include_market_news
    )
    
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
@click.option("--provider", default="yahoo", type=click.Choice(["yahoo", "finnhub"]), help="Data provider")
@click.option("--force", is_flag=True, help="Bypass cache")
def news(ticker, provider, force):
    """Fetch recent news."""
    
    if provider == "yahoo":
        key = f"yahoo:news:{ticker}:latest"
        fetch_func = lambda: yahoo.fetch_news(ticker)
        
    elif provider == "finnhub":
        # Strategy for Finnhub "latest": fetch last 7 days?
        # PLANS.md said "news_{days}d.json" but we generalized to "latest" for cache key simpler.
        # Let's define "latest" as last 7 days for Finnhub too.
        end_d = date.today()
        start_d = end_d - timedelta(days=7)
        # We include dates in key to be correct if we changed ranges?
        # Actually for 'latest' concept, we overwrite.
        key = f"finnhub:news:{ticker}:latest"
        fetch_func = lambda: finnhub.fetch_company_news(ticker, start_d, end_d)

    if not force:
        cached = cache.get(key)
        if cached:
            _print_json(cached, cached=True)
            return

    items = fetch_func()
    as_dict = [i.model_dump(mode='json') for i in items]
    
    cache.put(key, as_dict)
    _print_json(as_dict, cached=False)

@fetch.command("market-news")
@click.option("--category", default="general", help="Finnhub market news category (default: general)")
@click.option("--min-id", default=0, type=int, help="Finnhub minId for pagination")
@click.option("--force", is_flag=True, help="Bypass cache")
def market_news(category, min_id, force):
    """Fetch broad market news from Finnhub."""
    category = (category or "").strip()
    if not category:
        raise click.BadParameter("Category must be a non-empty string.")
    if min_id < 0:
        raise click.BadParameter("min-id must be >= 0.")

    key = f"finnhub:market_news:{category}:{min_id}"

    if not force:
        cached = cache.get(key)
        if cached:
            _print_json(cached, cached=True)
            return

    items = finnhub.fetch_market_news(category=category, min_id=min_id)
    as_dict = [i.model_dump(mode="json") for i in items]

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
