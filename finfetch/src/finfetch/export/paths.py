from pathlib import Path

def get_export_dir(ticker: str, root: str = "./exports") -> Path:
    """
    Get (and create) export directory for a ticker.
    Structure: {root}/{ticker}/
    """
    path = Path(root) / ticker
    path.mkdir(parents=True, exist_ok=True)
    return path
