from pathlib import Path
from typing import List, Dict, Any

def export_fundamentals_md(data: Dict[str, Any], path: Path):
    """Export fundamentals to Markdown."""
    lines = []
    lines.append(f"# Fundamentals: {data.get('symbol', 'UNKNOWN')}")
    lines.append("")
    
    lines.append(f"**Name**: {data.get('name')}")
    lines.append(f"**Sector**: {data.get('sector')} | **Industry**: {data.get('industry')}")
    lines.append(f"**Market Cap**: {data.get('market_cap')}")
    lines.append("")
    
    lines.append("## Valuation")
    lines.append(f"- Trailing PE: {data.get('trailingPE')}")
    lines.append(f"- Forward PE: {data.get('forwardPE')}")
    lines.append("")
    
    lines.append("## Details")
    # Dump a few key details if available
    details = data.get('details', {})
    if details:
        lines.append(f"- Zip: {details.get('zip')}")
        lines.append(f"- Website: {details.get('website')}")
        
        # Summary/Profile
        summary = details.get('longBusinessSummary')
        if summary:
            lines.append("")
            lines.append("### Business Summary")
            lines.append(summary)

    with open(path, 'w') as f:
        f.write("\n".join(lines))

def export_news_md(data: List[Dict[str, Any]], path: Path):
    """Export news to Markdown."""
    lines = []
    lines.append("# Recent News")
    lines.append("")
    
    for item in data:
        lines.append(f"## {item.get('title')}")
        lines.append(f"**Source**: {item.get('source')} | **Date**: {item.get('published_at')}")
        lines.append(f"[Read Article]({item.get('url')})")
        lines.append("")
        
    with open(path, 'w') as f:
        f.write("\n".join(lines))


def export_transcript_md(transcript: Dict[str, Any], path: Path):
    """Export an earnings call transcript to Markdown."""
    lines: List[str] = []
    title = transcript.get("title") or "Earnings Call Transcript"
    lines.append(f"# {title}")
    lines.append("")

    meta_pairs = [
        ("Ticker", transcript.get("symbol")),
        ("Company", transcript.get("company")),
        ("Quarter", transcript.get("quarter")),
        ("Event Date", transcript.get("event_date")),
        ("Source", transcript.get("url")),
    ]
    lines.append("## Summary")
    for label, value in meta_pairs:
        if value:
            lines.append(f"- **{label}**: {value}")
    lines.append("")

    lines.append("## Transcript")
    for section in transcript.get("sections", []):
        speaker = section.get("speaker") or "Narrator"
        role = section.get("role")
        heading = f"### {speaker}"
        if role:
            heading += f" — {role}"
        lines.append(heading)
        lines.append("")
        text = section.get("text", "")
        lines.append(text)
        lines.append("")

    lines.append("## Full Text")
    lines.append(transcript.get("full_text", ""))

    with open(path, "w") as f:
        f.write("\n".join(lines))
