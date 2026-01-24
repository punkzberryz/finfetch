from pathlib import Path
from typing import List, Dict, Any
import yaml
from .errors import ValidationError

def load_portfolio(path: str = "portfolio.yaml") -> Dict[str, Any]:
    """
    Load a single-portfolio config from YAML.
    Expected shape:
      portfolio:
        name: "My Portfolio"
        tickers: [AAPL, MSFT]
    """
    p = Path(path)
    if not p.exists():
        raise ValidationError(f"Portfolio file not found: {path}")

    try:
        data = yaml.safe_load(p.read_text()) or {}
    except Exception as e:
        raise ValidationError(f"Invalid portfolio YAML: {e}")

    if "portfolio" not in data or not isinstance(data["portfolio"], dict):
        raise ValidationError("Portfolio file must contain a 'portfolio' object.")

    portfolio = data["portfolio"]
    name = portfolio.get("name") or "Portfolio"
    tickers = portfolio.get("tickers")

    if not isinstance(tickers, list) or not tickers:
        raise ValidationError("'portfolio.tickers' must be a non-empty list.")

    norm = []
    for t in tickers:
        if not isinstance(t, str) or not t.strip():
            raise ValidationError("All tickers must be non-empty strings.")
        norm.append(t.strip().upper())

    return {"name": name, "tickers": norm}
