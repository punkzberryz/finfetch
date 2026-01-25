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
from .digest import daily as daily_digest
from .portfolio import load_portfolio
from .market import load_market
from pathlib import Path

# Configure logging at module level
configure_logging()
cache = SQLiteCache()

def _ensure_cache(tickers, *, include_market_news: bool) -> None:
    for ticker in tickers:
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

    if include_market_news:
        key_market = "finnhub:market_news:general:0"
        if not cache.get(key_market):
            try:
                items = finnhub.fetch_market_news(category="general", min_id=0)
                cache.put(key_market, [i.model_dump(mode="json") for i in items])
            except FinFetchError:
                pass
            except Exception:
                pass

@click.group()
def cli():
    """finfetch: Financial data fetcher."""
    pass

# ... (omitted)

@cli.command()
@click.option("--type", "digest_type", type=click.Choice(["daily", "weekly"]), required=True, help="Digest type")
@click.option("--date", "digest_date", required=False, help="Digest date (YYYY-MM-DD, daily only)")
@click.option("--portfolio", is_flag=True, help="Use portfolio.yaml (weekly only)")
@click.option("--out", default="./exports", help="Export root directory")
def digest(digest_type, digest_date, portfolio, out):
    """
    High-level digest orchestration.
    Loads tickers from YAML, fetches missing cache data, then generates digest output.
    """
    if portfolio and digest_type != "weekly":
        raise click.BadParameter("--portfolio can only be used with --type weekly.")

    if digest_date and digest_type != "daily":
        raise click.BadParameter("--date can only be used with --type daily.")

    day = None
    if digest_date:
        try:
            day = date.fromisoformat(digest_date)
        except ValueError:
            raise click.BadParameter("date must be in YYYY-MM-DD format.")

    if portfolio:
        portfolio_data = load_portfolio()
        ticker_list = portfolio_data["tickers"]
        title = f"# Portfolio Digest: {portfolio_data['name']} ({date.today().isocalendar()[0]}-W{date.today().isocalendar()[1]:02d})"
        out_dir = Path(out) / "portfolio"
        include_market_news = False
    else:
        market_data = load_market()
        ticker_list = market_data["tickers"]
        if digest_type == "weekly":
            title = f"# Market Digest: {market_data['name']} ({date.today().isocalendar()[0]}-W{date.today().isocalendar()[1]:02d})"
        else:
            day_label = (day or date.today()).isoformat()
            title = f"# Market Digest: {market_data['name']} ({day_label})"
        out_dir = Path(out) / "digests"
        include_market_news = True

    _ensure_cache(ticker_list, include_market_news=include_market_news)

    if digest_type == "weekly":
        report_path = weekly_digest.generate_weekly_digest(
            ticker_list,
            out_dir,
            title=title,
            include_market_news=include_market_news,
        )
        _print_json({
            "digest_file": str(report_path),
            "tickers": ticker_list,
            "type": "weekly",
        })
    else:
        report_path = daily_digest.generate_daily_digest(
            ticker_list,
            out_dir,
            digest_date=day,
            include_market_news=include_market_news,
        )
        _print_json({
            "digest_file": str(report_path),
            "tickers": ticker_list,
            "type": "daily",
            "date": (day or date.today()).isoformat(),
        })


@cli.group(name="fetch-digest")
def fetch_digest():
    """Generate digests from cache only."""
    pass


@fetch_digest.command()
@click.option("--tickers", required=False, help="Comma-separated tickers (e.g. AAPL,MSFT)")
@click.option("--out", default="./exports", help="Export root directory")
@click.option("--portfolio", is_flag=True, help="Use tickers from portfolio.yaml")
def weekly(tickers, out, portfolio):
    """
    Generate a weekly digest for the given tickers.
    Reads from existing cache only.
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

    report_path = weekly_digest.generate_weekly_digest(
        ticker_list,
        out_dir,
        title=title,
        include_market_news=include_market_news,
    )

    _print_json({
        "digest_file": str(report_path),
        "tickers": ticker_list,
        "type": "weekly",
    })


@fetch_digest.command()
@click.option("--tickers", required=True, help="Comma-separated tickers (e.g. AAPL,MSFT)")
@click.option("--date", "digest_date", required=False, help="Digest date (YYYY-MM-DD)")
@click.option("--out", default="./exports", help="Export root directory")
def daily(tickers, digest_date, out):
    """
    Generate a daily digest for the given tickers.
    Reads from existing cache only and filters news to the specified date.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(',') if t.strip()]
    if not ticker_list:
        raise click.BadParameter("tickers must include at least one symbol.")

    day = None
    if digest_date:
        try:
            day = date.fromisoformat(digest_date)
        except ValueError:
            raise click.BadParameter("date must be in YYYY-MM-DD format.")

    out_dir = Path(out) / "digests"
    report_path = daily_digest.generate_daily_digest(
        ticker_list,
        out_dir,
        digest_date=day,
        include_market_news=True,
    )

    _print_json({
        "digest_file": str(report_path),
        "tickers": ticker_list,
        "type": "daily",
        "date": (day or date.today()).isoformat(),
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
        
    # 2b. Financials (annual/quarterly statements)
    key_fin = f"yahoo:financials:{ticker}"
    data_fin = cache.get(key_fin)
    if data_fin:
        csv_export.export_financials_csv(data_fin, export_dir, ticker)
        results.append("financials_csv")

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

@fetch.command()
@click.option("--ticker", required=True, help="Stock ticker symbol")
@click.option("--force", is_flag=True, help="Bypass cache")
def financials(ticker, force):
    """Fetch annual and quarterly financial statements."""
    ticker = (ticker or "").strip().upper()
    if not ticker:
        raise click.BadParameter("ticker must be a non-empty symbol.")

    key = f"yahoo:financials:{ticker}"

    if not force:
        cached = cache.get(key)
        if cached:
            _print_json(cached, cached=True)
            return

    data = yahoo.fetch_financials(ticker)
    cache.put(key, data)
    _print_json(data, cached=False)

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
