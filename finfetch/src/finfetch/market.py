from pathlib import Path
from typing import Dict, Any
import yaml
from .errors import ValidationError


def load_market(path: str = "market.yaml") -> Dict[str, Any]:
    """
    Load market digest config from YAML.
    Expected shape:
      market:
        name: "Market Digest"
        tickers: [AAPL, MSFT]
    """
    p = Path(path)
    if not p.exists():
        raise ValidationError(f"Market file not found: {path}")

    try:
        data = yaml.safe_load(p.read_text()) or {}
    except Exception as e:
        raise ValidationError(f"Invalid market YAML: {e}")

    if "market" not in data or not isinstance(data["market"], dict):
        raise ValidationError("Market file must contain a 'market' object.")

    market = data["market"]
    name = market.get("name") or "Market Digest"
    tickers = market.get("tickers")

    if not isinstance(tickers, list) or not tickers:
        raise ValidationError("'market.tickers' must be a non-empty list.")

    norm = []
    for t in tickers:
        if not isinstance(t, str) or not t.strip():
            raise ValidationError("All tickers must be non-empty strings.")
        norm.append(t.strip().upper())

    return {"name": name, "tickers": norm}
