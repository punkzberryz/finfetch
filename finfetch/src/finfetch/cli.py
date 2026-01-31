import sys
import json
import click
import hashlib
import re
import logging
import concurrent.futures
from .errors import format_error, FinFetchError
from .logging import configure_logging
from .models.fundamentals import FundamentalsSnapshot
from .models.prices import PriceBar
from .models.news import NewsItem
from .providers import yahoo, finnhub
from datetime import date, timedelta
from .cache.sqlite import SQLiteCache
from .cache.transcripts import TranscriptStore
from .export.paths import get_export_dir
from .export import json_export, csv_export, md_export, transcript_export
from .digest import weekly as weekly_digest
from .digest import daily as daily_digest
from .portfolio import load_portfolio
from .market import load_market
from pathlib import Path

# Configure logging at module level
configure_logging()
cache = SQLiteCache()
transcript_store = TranscriptStore()
logger = logging.getLogger(__name__)

def _ensure_cache(tickers, *, include_market_news: bool, max_workers: int) -> None:
    def _ensure_ticker(ticker: str) -> None:
        logger.info(f"Ensuring cache for {ticker}")

        key_fund = f"yahoo:fundamentals:{ticker}"
        if not cache.get(key_fund):
            logger.info(f"Fetching fundamentals (Yahoo) for {ticker}")
            data = yahoo.fetch_fundamentals(ticker)
            cache.put(key_fund, data.model_dump(mode="json", by_alias=True))
        else:
            logger.info(f"Cache hit: fundamentals (Yahoo) for {ticker}")

        key_price = f"yahoo:prices:{ticker}:5d:1d"
        if not cache.get(key_price):
            logger.info(f"Fetching prices (Yahoo) for {ticker} (5d/1d)")
            bars = yahoo.fetch_prices(ticker, "5d", "1d")
            cache.put(key_price, [b.model_dump(mode="json") for b in bars])
        else:
            logger.info(f"Cache hit: prices (Yahoo) for {ticker} (5d/1d)")

        key_news = f"yahoo:news:{ticker}:latest"
        if not cache.get(key_news):
            logger.info(f"Fetching news (Yahoo) for {ticker}")
            items = yahoo.fetch_news(ticker)
            cache.put(key_news, [i.model_dump(mode="json") for i in items])
        else:
            logger.info(f"Cache hit: news (Yahoo) for {ticker}")

        key_finnhub = f"finnhub:news:{ticker}:latest"
        if not cache.get(key_finnhub):
            try:
                logger.info(f"Fetching company news (Finnhub) for {ticker}")
                end_d = date.today()
                start_d = end_d - timedelta(days=7)
                items = finnhub.fetch_company_news(ticker, start_d, end_d)
                cache.put(key_finnhub, [i.model_dump(mode="json") for i in items])
            except FinFetchError:
                pass
            except Exception:
                pass
        else:
            logger.info(f"Cache hit: company news (Finnhub) for {ticker}")

        logger.info(f"Finished cache for {ticker}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_ensure_ticker, ticker) for ticker in tickers]
        for fut in concurrent.futures.as_completed(futures):
            fut.result()

    if include_market_news:
        key_market = "finnhub:market_news:general:0"
        if not cache.get(key_market):
            try:
                logger.info("Fetching market news (Finnhub) category=general")
                items = finnhub.fetch_market_news(category="general", min_id=0)
                cache.put(key_market, [i.model_dump(mode="json") for i in items])
            except FinFetchError:
                pass
            except Exception:
                pass
        else:
            logger.info("Cache hit: market news (Finnhub) category=general")


_TRANSCRIPT_URL_RE = re.compile(
    r"^https?://finance\.yahoo\.com/quote/[A-Za-z\.-]+/earnings/.*", re.IGNORECASE
)


def _validate_transcript_url(ctx, param, value):
    url = (value or "").strip()
    if not url or not _TRANSCRIPT_URL_RE.match(url):
        raise click.BadParameter("url must be a Yahoo Finance earnings call transcript link.")
    return url


@click.group()
def scrape():
    """Scrape HTML-based sources."""
    pass


@scrape.command("transcript")
@click.option("--url", "transcript_url", required=True, callback=_validate_transcript_url, help="Yahoo Finance transcript URL")
@click.option("--out", default="./exports", help="Export root directory")
@click.option("--force", is_flag=True, help="Re-scrape even if cached")
def scrape_transcript(transcript_url, out, force):
    """
    Scrape a Yahoo Finance earnings call transcript and export JSON + Markdown.
    """
    if not force:
        cached = transcript_store.get(transcript_url)
        if cached:
            exports = transcript_export.export_transcript(cached, out_root=out)
            _print_json({"transcript": cached, "exports": exports}, cached=True)
            return

    transcript = yahoo.scrape_transcript(transcript_url)
    transcript_store.upsert(transcript)
    payload = transcript.model_dump(mode="json", by_alias=True)
    exports = transcript_export.export_transcript(payload, out_root=out)
    _print_json({"transcript": payload, "exports": exports}, cached=False)


@click.group()
def cli():
    """finfetch: Financial data fetcher."""
    pass

cli.add_command(scrape)

# ... (omitted)

@cli.command()
@click.option("--type", "digest_type", type=click.Choice(["daily", "weekly"]), required=True, help="Digest type")
@click.option("--date", "digest_date", required=False, help="Digest date (YYYY-MM-DD, daily only)")
@click.option("--portfolio", is_flag=True, help="Use portfolio.yaml (weekly only)")
@click.option("--out", default="./exports", help="Export root directory")
@click.option("--workers", default=4, show_default=True, type=int, help="Max parallel workers for cache hydration")
def digest(digest_type, digest_date, portfolio, out, workers):
    """
    High-level digest orchestration.
    Loads tickers from YAML, fetches missing cache data, then generates digest output.
    """
    logger.info("Starting digest orchestration")
    if workers < 1:
        raise click.BadParameter("--workers must be >= 1.")

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
        logger.info(f"Loaded {len(ticker_list)} portfolio tickers")
        title = f"# Portfolio Digest: {portfolio_data['name']} ({date.today().isocalendar()[0]}-W{date.today().isocalendar()[1]:02d})"
        out_dir = Path(out) / "portfolio"
        include_market_news = False
    else:
        market_data = load_market()
        ticker_list = market_data["tickers"]
        logger.info(f"Loaded {len(ticker_list)} market tickers")
        if digest_type == "weekly":
            title = f"# Market Digest: {market_data['name']} ({date.today().isocalendar()[0]}-W{date.today().isocalendar()[1]:02d})"
        else:
            day_label = (day or date.today()).isoformat()
            title = f"# Market Digest: {market_data['name']} ({day_label})"
        out_dir = Path(out) / "digests"
        include_market_news = True

    logger.info(f"Ensuring cache (include_market_news={include_market_news}, workers={workers})")
    _ensure_cache(ticker_list, include_market_news=include_market_news, max_workers=workers)

    if digest_type == "weekly":
        logger.info("Generating weekly digest")
        report_path = weekly_digest.generate_weekly_digest(
            ticker_list,
            out_dir,
            title=title,
            include_market_news=include_market_news,
        )
        logger.info(f"Digest written to {report_path}")
        _print_json({
            "digest_file": str(report_path),
            "tickers": ticker_list,
            "type": "weekly",
        })
    else:
        logger.info("Generating daily digest")
        report_path = daily_digest.generate_daily_digest(
            ticker_list,
            out_dir,
            digest_date=day,
            include_market_news=include_market_news,
        )
        logger.info(f"Digest written to {report_path}")
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
