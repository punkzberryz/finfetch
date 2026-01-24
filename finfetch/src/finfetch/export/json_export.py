import json
from pathlib import Path
from typing import Any

def export_json(data: Any, path: Path):
    """
    Export data to JSON file.
    """
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True, default=str)
