#!/usr/bin/env python
import argparse
import sys
from pathlib import Path

import yaml


def load_tickers(path: Path):
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or {}
    tickers = (data.get("market") or {}).get("tickers") or []
    return [t.strip().upper() for t in tickers if isinstance(t, str) and t.strip()]


def main():
    parser = argparse.ArgumentParser(description="Print market tickers as CSV.")
    parser.add_argument(
        "--path",
        default="market.yaml",
        help="Path to market YAML file",
    )
    args = parser.parse_args()

    tickers = load_tickers(Path(args.path))
    if not tickers:
        print(f"No tickers found in {args.path}", file=sys.stderr)
        return 1
    print(",".join(tickers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
