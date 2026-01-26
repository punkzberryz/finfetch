import csv
import datetime
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from ..cache.sqlite import SQLiteCache

# Initialize cache for reading
cache = SQLiteCache()

_POS_WORDS = {
    "beat", "beats", "surge", "surges", "soar", "soars", "soared",
    "record", "strong", "stronger", "growth", "profit", "profits",
    "up", "upgrade", "upgrades", "bull", "bullish", "raises", "raise",
    "accelerate", "accelerates", "wins", "win", "positive", "guidance"
}
_NEG_WORDS = {
    "miss", "misses", "slump", "slumps", "drop", "drops", "dropped",
    "weak", "weaker", "decline", "declines", "down", "downgrade",
    "downgrades", "bear", "bearish", "cuts", "cut", "slowdown",
    "loss", "losses", "negative", "warning", "warns"
}

_STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "over",
    "after", "before", "ahead", "amid", "as", "at", "by", "on", "in",
    "to", "of", "a", "an", "is", "are", "be", "its", "it", "their",
    "shares", "stock", "stocks", "company", "corp", "inc", "ltd",
    "co", "report", "reports", "quarter", "q1", "q2", "q3", "q4",
    "year", "years", "says", "said", "saying"
}

def _parse_datetime(value: Any) -> Optional[datetime.datetime]:
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(value)
        except Exception:
            return None
    if isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value)
        except Exception:
            return None
    return None

def _format_compact(value: Any, currency: Optional[str] = None) -> str:
    try:
        num = float(value)
    except Exception:
        return "N/A"
    sign = "-" if num < 0 else ""
    num = abs(num)
    if num >= 1_000_000_000_000:
        out = f"{sign}{num / 1_000_000_000_000:.2f}T"
    elif num >= 1_000_000_000:
        out = f"{sign}{num / 1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        out = f"{sign}{num / 1_000_000:.2f}M"
    elif num >= 1_000:
        out = f"{sign}{num / 1_000:.2f}K"
    else:
        out = f"{sign}{num:.2f}"
    if currency:
        return f"{currency} {out}"
    return out

def _format_ratio(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "N/A"

def _get_first_key(data: Dict[str, Any], keys: List[str]) -> Any:
    for key in keys:
        if key in data and data.get(key) is not None:
            return data.get(key)
    return None

def _normalize_news(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    seen = set()
    for item in items:
        key = item.get("id") or item.get("url") or item.get("title")
        if key in seen:
            continue
        seen.add(key)
        dt = _parse_datetime(item.get("published_at") or item.get("publishedAt"))
        normalized.append({
            "id": item.get("id"),
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "source": item.get("source", "Unknown"),
            "published_at": dt,
            "provider": item.get("provider", "unknown")
        })
    normalized.sort(key=lambda x: x.get("published_at") or datetime.datetime.min, reverse=True)
    return normalized

def _headline_sentiment(title: str) -> int:
    words = set(re.findall(r"[a-z0-9]+", title.lower()))
    pos = any(w in _POS_WORDS for w in words)
    neg = any(w in _NEG_WORDS for w in words)
    if pos and not neg:
        return 1
    if neg and not pos:
        return -1
    return 0

def _weighted_sentiment(news: List[Dict[str, Any]]) -> Tuple[str, float]:
    if not news:
        return ("Neutral", 0.0)
    total_weight = 0.0
    score_sum = 0.0
    now = datetime.datetime.now()
    for item in news:
        sentiment = _headline_sentiment(item.get("title", ""))
        dt = item.get("published_at")
        if isinstance(dt, datetime.datetime):
            days = max(0.0, (now - dt).days)
            weight = max(0.2, 1.0 - (days / 7.0))
        else:
            weight = 0.5
        total_weight += weight
        score_sum += sentiment * weight
    if total_weight == 0:
        return ("Neutral", 0.0)
    score = score_sum / total_weight
    if score >= 0.15:
        return ("Positive", score)
    if score <= -0.15:
        return ("Negative", score)
    return ("Neutral", score)

def _extract_themes(news: List[Dict[str, Any]], limit: int = 6) -> List[Tuple[str, int]]:
    counts: Dict[str, int] = {}
    for item in news:
        words = re.findall(r"[a-z0-9]+", item.get("title", "").lower())
        for w in words:
            if len(w) < 3 or w in _STOP_WORDS:
                continue
            counts[w] = counts.get(w, 0) + 1
    items = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    return items[:limit]

def _build_prompt(title: str, rows: List[Dict[str, str]], *, digest_date: Optional[datetime.date] = None) -> str:
    day = digest_date or datetime.date.today()
    today = day.isoformat()
    lines = []
    lines.append("You are a financial research assistant. Visit each link below, extract the key facts, and write a market digest report in Markdown.")
    lines.append("")
    lines.append("Requirements:")
    lines.append("- Sections: TL;DR (3 bullets), Key Takeaways (1-2 bullets), In-Depth (120-200 words per source)")
    lines.append("- Include citations as inline links for every non-trivial claim")
    lines.append("- Keep tone neutral and factual")
    lines.append("- Output Markdown only")
    lines.append("")
    lines.append(f"# {title} ({today})")
    lines.append("")
    lines.append("## Sources")
    idx = 1
    for row in rows:
        url = (row.get("url") or "").strip()
        if not url:
            continue
        label = row.get("title") or url
        meta = []
        if row.get("source"):
            meta.append(row["source"])
        if row.get("ticker"):
            meta.append(row["ticker"])
        if row.get("published_at"):
            meta.append(row["published_at"])
        meta_str = " | ".join(meta)
        if meta_str:
            lines.append(f"{idx}. {label} ({meta_str}) — {url}")
        else:
            lines.append(f"{idx}. {label} — {url}")
        idx += 1
    return "\n".join(lines)

def generate_weekly_digest(tickers: List[str], out_dir: Path, *, title: Optional[str] = None, include_market_news: bool = True) -> Path:
    """
    Generate a weekly digest markdown file for a list of tickers.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine ISO Week
    today = datetime.date.today()
    year, week, weekday = today.isocalendar()
    filename = f"weekly_{year}-W{week:02d}.md"
    out_path = out_dir / filename
    csv_path = out_dir / f"weekly_{year}-W{week:02d}_news_links.csv"
    prompt_path = out_dir / f"weekly_{year}-W{week:02d}_prompt.txt"
    
    tickers_sorted = sorted([t.upper() for t in tickers])
    today_str = today.isoformat()

    ticker_data: Dict[str, Dict[str, Any]] = {}
    all_news: List[Dict[str, Any]] = []
    csv_rows: List[Dict[str, str]] = []

    for ticker in tickers_sorted:
        fund = cache.get(f"yahoo:fundamentals:{ticker}") or {}
        prices = cache.get(f"yahoo:prices:{ticker}:5d:1d") or []

        yahoo_news = cache.get(f"yahoo:news:{ticker}:latest") or []
        finnhub_news = cache.get(f"finnhub:news:{ticker}:latest") or []
        merged_news = _normalize_news(yahoo_news + finnhub_news)
        all_news.extend(merged_news)

        change = None
        start_price = None
        end_price = None
        if prices and len(prices) >= 2:
            start_price = prices[0].get("close")
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
            "news": merged_news
        }

    lines = []
    lines.append(title or f"# Weekly Market Digest: {year}-W{week:02d}")
    lines.append(f"**Date**: {today_str}")
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
        lines.append(f"- Weekly breadth: {up} up / {down} down")
        lines.append(f"- Average change: {avg_change:.2f}%")
        lines.append(f"- Best performer: {best[0]} ({best[1].get('change'):.2f}%)")
        lines.append(f"- Worst performer: {worst[0]} ({worst[1].get('change'):.2f}%)")
    else:
        lines.append("- Not enough price data to summarize weekly performance.")
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
                    "provider": item.get("provider", "")
                })
        else:
            lines.append("- No cached market news.")
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
            lines.append(f"- Weekly change: {change:.2f}% ({data['start_price']:.2f} -> {data['end_price']:.2f})")
        else:
            lines.append("- Weekly change: N/A (Missing 5d price history)")

        # Sentiment
        sentiment_payload = cache.get(f"finnhub:sentiment:{ticker}:latest") or cache.get(f"finnhub:sentiment:{ticker}")
        if isinstance(sentiment_payload, dict):
            label = sentiment_payload.get("label") or sentiment_payload.get("sentiment") or "Unknown"
            score = sentiment_payload.get("score")
            score_str = _format_ratio(score) if score is not None else "N/A"
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
                    "provider": item.get("provider", "")
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
        
    with open(out_path, 'w') as f:
        f.write("\n".join(lines))

    # Export news links CSV (market + ticker headlines)
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["scope", "ticker", "source", "title", "url", "published_at", "provider"]
        )
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)

    # Export prompt text alongside digest outputs
    prompt_title = (title or f"Weekly Market Digest: {year}-W{week:02d}").replace("# ", "")
    prompt = _build_prompt(prompt_title, csv_rows)
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
        market_snapshot = {"note": "Not enough price data to summarize weekly performance."}

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
        "type": "weekly",
        "date": today_str,
        "week": f"{year}-W{week:02d}",
        "title": title or f"# Weekly Market Digest: {year}-W{week:02d}",
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

    json_path = out_dir / f"weekly_{year}-W{week:02d}.json"
    with open(json_path, "w") as f:
        json.dump(json_payload, f, indent=2, sort_keys=True)
        
    return out_path
