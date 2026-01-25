import csv
from pathlib import Path
from typing import List, Dict, Any

def export_fundamentals_csv(data: Dict[str, Any], path: Path):
    """Export fundamentals to vertical CSV (Key, Value)."""
    # Flatten specific fields, then dump details
    rows = []
    
    # Prioritize specific fields
    priority_fields = ['symbol', 'name', 'sector', 'industry', 'market_cap', 'currency']
    for k in priority_fields:
        if k in data:
            rows.append((k, data[k]))
            
    # Add everything else from top level if not dict
    for k, v in data.items():
        if k not in priority_fields and k != 'details' and not isinstance(v, (dict, list)):
            rows.append((k, v))
            
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Field', 'Value'])
        writer.writerows(rows)

def export_prices_csv(data: List[Dict[str, Any]], path: Path):
    """Export prices to standard CSV."""
    if not data:
        return

    # Assume strict schema from Pydantic
    headers = data[0].keys()
    
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def export_news_csv(data: List[Dict[str, Any]], path: Path):
    """Export news to CSV."""
    if not data:
        return
        
    headers = ['published_at', 'title', 'source', 'url', 'id']
    
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)


def export_financials_csv(data: Dict[str, Any], out_dir: Path, ticker: str):
    """Export financial statements to CSV files (annual/quarterly)."""
    statements = [
        ("income_statement", "income_statement"),
        ("balance_sheet", "balance_sheet"),
        ("cashflow", "cashflow"),
    ]

    for key, name in statements:
        block = data.get(key, {})
        if not isinstance(block, dict):
            continue
        for period in ("annual", "quarterly"):
            rows = block.get(period, [])
            if not rows:
                continue
            headers = list(rows[0].keys())
            filename = f"{ticker}_{name}_{period}.csv"
            path = out_dir / filename
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
