import os
import logging
from pathlib import Path

# Naive dotenv loader since we want to avoid extra dependencies if possible,
# or just assume user sources it. But Python standard way is `python-dotenv`.
# For M4, let's implement a simple .env reader to keep deps low, or use os.environ.
# User instruction said "help me create env file", implies we read it.

logger = logging.getLogger(__name__)

def load_env_file(path: str = ".env"):
    """
    Load environment variables from a .env file into os.environ.
    Does not override existing strings.
    """
    p = Path(path)
    if not p.exists():
        return
        
    try:
        with open(p) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    key = key.strip()
                    val = val.strip()
                    if key not in os.environ:
                        os.environ[key] = val
    except Exception as e:
        logger.warning(f"Failed to load .env: {e}")

# Load on import
load_env_file()

def get_finnhub_key() -> str:
    """Get Finnhub API Key or raise error if missing."""
    key = os.environ.get("FINNHUB_API_KEY")
    # Handle the template default left by user
    if not key or key == "your_key_here":
        return None
    return key
