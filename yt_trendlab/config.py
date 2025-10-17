"""yt_trendlab configuration defaults

Edit this file to set project-wide defaults so you don't need to pass them
on every command line. It's safe to set DEFAULT_OUT_DIR here; avoid committing
secrets. If you want to store an API key here, set API_KEY = 'YOUR_KEY' but be
careful with VCS.
"""
from pathlib import Path

# Optional: hard-code your API key here (not recommended for public repos)
API_KEY = "AIzaSyApavwxqaBLkNyK65iHdgmUf9eX5CsYrmI"

# Defaults used by get_trending.py and other utilities
DEFAULT_REGION = "JP"
DEFAULT_MAX = 200
DEFAULT_CATEGORY = None  # e.g. '24'
DEFAULT_OUT_DIR = str(Path("trend_data"))
DEFAULT_EXCLUDE_SHORTS = False
