import datetime
from pathlib import Path
from typing import List, Dict, Any
from ..cache.sqlite import SQLiteCache

# Initialize cache for reading
cache = SQLiteCache()

def generate_weekly_digest(tickers: List[str], out_dir: Path) -> Path:
    """
    Generate a weekly digest markdown file for a list of tickers.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine ISO Week
    today = datetime.date.today()
    year, week, weekday = today.isocalendar()
    filename = f"weekly_{year}-W{week:02d}.md"
    out_path = out_dir / filename
    
    lines = []
    lines.append(f"# Weekly Market Digest: {year}-W{week:02d}")
    lines.append(f"**Date**: {today}")
    lines.append("")
    
    for ticker in tickers:
        lines.append("---")
        lines.append(f"## {ticker}")
        
        # 1. Fundamentals
        key_fund = f"yahoo:fundamentals:{ticker}"
        fund = cache.get(key_fund)
        if fund:
            name = fund.get('name', 'Unknown')
            sector = fund.get('sector', 'N/A')
            pe = fund.get('trailingPE', 'N/A')
            lines.append(f"**{name}** ({sector})")
            lines.append(f"**Valuation**: P/E {pe} | **Mkt Cap**: {fund.get('market_cap','N/A')}")
        else:
            lines.append(f"*(No cached fundamentals)*")
            
        # 2. Performance (using 5d prices if available)
        key_price = f"yahoo:prices:{ticker}:5d:1d"
        prices = cache.get(key_price)
        if prices and len(prices) >= 2:
            start_price = prices[0].get('close')
            end_price = prices[-1].get('close')
            if start_price:
                change = ((end_price - start_price) / start_price) * 100
                emoji = "🟢" if change >= 0 else "🔴"
                lines.append(f"**Weekly Change**: {emoji} {change:.2f}% ({start_price:.2f} -> {end_price:.2f})")
        else:
            lines.append("**Weekly Change**: N/A (Missing 5d price history)")
            
        lines.append("")
        
        # 3. News
        key_news = f"yahoo:news:{ticker}:latest"
        news_items = cache.get(key_news)
        if news_items:
            lines.append("### Key Headlines")
            # Take top 3
            for item in news_items[:3]:
                title = item.get('title', 'No Title')
                source = item.get('source', 'Unknown')
                url = item.get('url', '#')
                lines.append(f"- **{source}**: [{title}]({url})")
        else:
            lines.append("*(No recent news)*")
            
        lines.append("")
        
    with open(out_path, 'w') as f:
        f.write("\n".join(lines))
        
    return out_path
