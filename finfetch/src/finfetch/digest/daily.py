import csv
import datetime
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..cache.sqlite import SQLiteCache
from .weekly import (
    _normalize_news,
    _weighted_sentiment,
    _headline_sentiment,
    _extract_themes,
    _build_prompt,
)

# Initialize cache for reading
cache = SQLiteCache()


def _filter_news_last_24h(
    items: List[Dict[str, Any]],
    *,
    end_time: Optional[datetime.datetime] = None,
) -> List[Dict[str, Any]]:
    end = end_time or datetime.datetime.now()
    start = end - datetime.timedelta(hours=24)
    filtered = []
    for item in items:
        dt = item.get("published_at")
        if isinstance(dt, datetime.datetime) and start <= dt <= end:
            filtered.append(item)
    return filtered


def generate_daily_digest(
    tickers: List[str],
    out_dir: Path,
    *,
    digest_date: Optional[datetime.date] = None,
    title: Optional[str] = None,
    include_market_news: bool = True,
) -> Path:
    """
    Generate a daily digest markdown file for a list of tickers.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    day = digest_date or datetime.date.today()
    day_str = day.isoformat()
    end_time = datetime.datetime.combine(day, datetime.time(23, 59, 59)) if digest_date else None
    filename = f"daily_{day_str}.md"
    out_path = out_dir / filename
    csv_path = out_dir / f"daily_{day_str}_news_links.csv"
    prompt_path = out_dir / f"daily_{day_str}_prompt.txt"

    tickers_sorted = sorted([t.upper() for t in tickers])

    ticker_data: Dict[str, Dict[str, Any]] = {}
    all_news: List[Dict[str, Any]] = []
    csv_rows: List[Dict[str, str]] = []

    for ticker in tickers_sorted:
        fund = cache.get(f"yahoo:fundamentals:{ticker}") or {}
        prices = cache.get(f"yahoo:prices:{ticker}:5d:1d") or []

        yahoo_news = cache.get(f"yahoo:news:{ticker}:latest") or []
        finnhub_news = cache.get(f"finnhub:news:{ticker}:latest") or []
        merged_news = _normalize_news(yahoo_news + finnhub_news)
        daily_news = _filter_news_last_24h(merged_news, end_time=end_time)
        all_news.extend(daily_news)

        change = None
        start_price = None
        end_price = None
        if prices and len(prices) >= 2:
            start_price = prices[-2].get("close")
            end_price = prices[-1].get("close")
            try:
                if start_price:
                    change = ((end_price - start_price) / start_price) * 100
            except Exception:
                change = None

        ticker_data[ticker] = {
            "fundamentals": fund,
            "prices": prices,
            "change": change,
            "start_price": start_price,
            "end_price": end_price,
            "news": daily_news,
        }

    lines = []
    lines.append(title or f"# Daily Market Digest: {day_str}")
    lines.append(f"**Date**: {day_str}")
    lines.append("")

    # Market Snapshot
    lines.append("## Market Snapshot")
    changes = [d["change"] for d in ticker_data.values() if isinstance(d.get("change"), (int, float))]
    if changes:
        avg_change = sum(changes) / len(changes)
        up = len([c for c in changes if c >= 0])
        down = len([c for c in changes if c < 0])
        best = max(ticker_data.items(), key=lambda x: x[1].get("change") if x[1].get("change") is not None else -9999)
        worst = min(ticker_data.items(), key=lambda x: x[1].get("change") if x[1].get("change") is not None else 9999)
        lines.append(f"- Daily breadth: {up} up / {down} down")
        lines.append(f"- Average change: {avg_change:.2f}%")
        lines.append(f"- Best performer: {best[0]} ({best[1].get('change'):.2f}%)")
        lines.append(f"- Worst performer: {worst[0]} ({worst[1].get('change'):.2f}%)")
    else:
        lines.append("- Not enough price data to summarize daily performance.")
    lines.append("")

    # Sector Rotation
    lines.append("## Sector Rotation")
    sector_map: Dict[str, List[float]] = {}
    for ticker, data in ticker_data.items():
        sector = (data["fundamentals"] or {}).get("sector") or "Unknown"
        change = data.get("change")
        if isinstance(change, (int, float)):
            sector_map.setdefault(sector, []).append(change)
    if sector_map:
        sector_items = []
        for sector, values in sector_map.items():
            sector_items.append((sector, sum(values) / len(values)))
        sector_items.sort(key=lambda x: (-x[1], x[0]))
        for sector, avg in sector_items:
            lines.append(f"- {sector}: {avg:.2f}%")
    else:
        lines.append("- Sector data not available.")
    lines.append("")

    # Top Themes
    lines.append("## Top Themes")
    themes = _extract_themes(all_news)
    if themes:
        for word, count in themes:
            lines.append(f"- {word} ({count})")
    else:
        lines.append("- No headline themes available.")
    lines.append("")

    if include_market_news:
        # Market News (broad, from Finnhub cache)
        lines.append("## Market News")
        market_news = cache.get("finnhub:market_news:general:0") or []
        market_items = _normalize_news(market_news)
        market_items = _filter_news_last_24h(market_items, end_time=end_time)
        if market_items:
            for item in market_items[:5]:
                title = item.get("title", "No Title")
                source = item.get("source", "Unknown")
                url = item.get("url", "#")
                lines.append(f"- {source}: [{title}]({url})")
                csv_rows.append({
                    "scope": "market",
                    "ticker": "",
                    "source": source,
                    "title": title,
                    "url": url,
                    "published_at": (item.get("published_at") or "").isoformat() if isinstance(item.get("published_at"), datetime.datetime) else "",
                    "provider": item.get("provider", ""),
                })
        else:
            lines.append("- No cached market news for this date.")
        lines.append("")

    # Ticker Highlights
    lines.append("## Ticker Highlights")
    for ticker in tickers_sorted:
        data = ticker_data[ticker]
        fund = data["fundamentals"] or {}
        news = data["news"]
        lines.append(f"### {ticker}")

        name = fund.get("name", "Unknown")
        sector = fund.get("sector", "N/A")
        industry = fund.get("industry", "N/A")
        lines.append(f"**{name}** | Sector: {sector} | Industry: {industry}")

        change = data.get("change")
        if isinstance(change, (int, float)) and data.get("start_price") and data.get("end_price"):
            lines.append(f"- Daily change: {change:.2f}% ({data['start_price']:.2f} -> {data['end_price']:.2f})")
        else:
            lines.append("- Daily change: N/A (Missing recent price history)")

        # Sentiment
        sentiment_payload = cache.get(f"finnhub:sentiment:{ticker}:latest") or cache.get(f"finnhub:sentiment:{ticker}")
        if isinstance(sentiment_payload, dict):
            label = sentiment_payload.get("label") or sentiment_payload.get("sentiment") or "Unknown"
            score = sentiment_payload.get("score")
            score_str = f"{float(score):.2f}" if score is not None else "N/A"
            lines.append(f"- Sentiment: {label} (Finnhub, score {score_str})")
        else:
            label, score = _weighted_sentiment(news)
            lines.append(f"- Sentiment: {label} (weighted, score {score:.2f})")

        # Headlines
        if news:
            lines.append("- Key headlines:")
            for item in news[:3]:
                title = item.get("title", "No Title")
                source = item.get("source", "Unknown")
                url = item.get("url", "#")
                lines.append(f"  - {source}: [{title}]({url})")
                csv_rows.append({
                    "scope": "ticker",
                    "ticker": ticker,
                    "source": source,
                    "title": title,
                    "url": url,
                    "published_at": (item.get("published_at") or "").isoformat() if isinstance(item.get("published_at"), datetime.datetime) else "",
                    "provider": item.get("provider", ""),
                })
        else:
            lines.append("- Key headlines: N/A")

        # Risks / Catalysts (derived from headlines)
        if news:
            lines.append("- Risks/Catalysts:")
            for item in news[:3]:
                title = item.get("title", "")
                tag = _headline_sentiment(title)
                label = "Catalyst" if tag > 0 else "Risk" if tag < 0 else "Neutral"
                lines.append(f"  - {label}: {title}")
        else:
            lines.append("- Risks/Catalysts: N/A")

        lines.append("")

    with open(out_path, "w") as f:
        f.write("\n".join(lines))

    # Export news links CSV (market + ticker headlines)
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["scope", "ticker", "source", "title", "url", "published_at", "provider"],
        )
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    # Export prompt text alongside digest outputs
    prompt_title = (title or f"Daily Market Digest: {day_str}").replace("# ", "")
    prompt = _build_prompt(prompt_title, csv_rows, digest_date=day)
    with open(prompt_path, "w") as f:
        f.write(prompt)

    def _iso(dt: Any) -> str:
        if isinstance(dt, datetime.datetime):
            return dt.isoformat()
        return ""

    market_snapshot = None
    if changes:
        market_snapshot = {
            "breadth": {"up": up, "down": down},
            "average_change": avg_change,
            "best": {"ticker": best[0], "change": best[1].get("change")},
            "worst": {"ticker": worst[0], "change": worst[1].get("change")},
        }
    else:
        market_snapshot = {"note": "Not enough price data to summarize daily performance."}

    sector_rotation = []
    if sector_map:
        sector_items = []
        for sector, values in sector_map.items():
            sector_items.append((sector, sum(values) / len(values)))
        sector_items.sort(key=lambda x: (-x[1], x[0]))
        for sector, avg in sector_items:
            sector_rotation.append({"sector": sector, "average_change": avg})

    top_themes = [{"theme": word, "count": count} for word, count in themes] if themes else []

    market_news_payload = []
    if include_market_news:
        market_news = cache.get("finnhub:market_news:general:0") or []
        market_items = _normalize_news(market_news)
        market_items = _filter_news_last_24h(market_items, end_time=end_time)
        for item in market_items[:5]:
            market_news_payload.append({
                "title": item.get("title", ""),
                "source": item.get("source", "Unknown"),
                "url": item.get("url", ""),
                "published_at": _iso(item.get("published_at")),
                "provider": item.get("provider", ""),
            })

    ticker_highlights = []
    for ticker in tickers_sorted:
        data = ticker_data[ticker]
        fund = data["fundamentals"] or {}
        news = data["news"]

        sentiment_payload = cache.get(f"finnhub:sentiment:{ticker}:latest") or cache.get(f"finnhub:sentiment:{ticker}")
        if isinstance(sentiment_payload, dict):
            sentiment = {
                "source": "finnhub",
                "label": sentiment_payload.get("label") or sentiment_payload.get("sentiment") or "Unknown",
                "score": sentiment_payload.get("score"),
            }
        else:
            label, score = _weighted_sentiment(news)
            sentiment = {
                "source": "weighted",
                "label": label,
                "score": score,
            }

        headlines = []
        risks_catalysts = []
        if news:
            for item in news[:3]:
                title = item.get("title", "No Title")
                headlines.append({
                    "title": title,
                    "source": item.get("source", "Unknown"),
                    "url": item.get("url", ""),
                    "published_at": _iso(item.get("published_at")),
                    "provider": item.get("provider", ""),
                })
                tag = _headline_sentiment(title)
                label = "Catalyst" if tag > 0 else "Risk" if tag < 0 else "Neutral"
                risks_catalysts.append({"label": label, "title": title})

        ticker_highlights.append({
            "ticker": ticker,
            "name": fund.get("name", "Unknown"),
            "sector": fund.get("sector", "N/A"),
            "industry": fund.get("industry", "N/A"),
            "change": data.get("change"),
            "start_price": data.get("start_price"),
            "end_price": data.get("end_price"),
            "sentiment": sentiment,
            "headlines": headlines,
            "risks_catalysts": risks_catalysts,
        })

    json_payload = {
        "type": "daily",
        "date": day_str,
        "title": title or f"# Daily Market Digest: {day_str}",
        "tickers": tickers_sorted,
        "include_market_news": include_market_news,
        "market_snapshot": market_snapshot,
        "sector_rotation": sector_rotation,
        "top_themes": top_themes,
        "market_news": market_news_payload,
        "ticker_highlights": ticker_highlights,
        "news_links": [
            {
                **row,
                "published_at": row.get("published_at") or "",
            }
            for row in csv_rows
        ],
    }

    json_path = out_dir / f"daily_{day_str}.json"
    with open(json_path, "w") as f:
        json.dump(json_payload, f, indent=2, sort_keys=True)

    return out_path
