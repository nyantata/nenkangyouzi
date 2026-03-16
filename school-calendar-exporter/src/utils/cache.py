import hashlib
import json
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)
CACHE_DIR = Path(__file__).parent.parent.parent / "cache"


def _cache_key(file_path: str) -> str:
    """Compute a cache key from the file content hash."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_cache(file_path: str) -> list[dict] | None:
    """Return cached events for *file_path*, or None if not cached."""
    CACHE_DIR.mkdir(exist_ok=True)
    key = _cache_key(file_path)
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        logger.info(f"Cache hit: {cache_file}")
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)
    logger.info(f"Cache miss for {file_path}")
    return None


def save_cache(file_path: str, events: list[dict]) -> None:
    """Persist *events* to the cache directory."""
    CACHE_DIR.mkdir(exist_ok=True)
    key = _cache_key(file_path)
    cache_file = CACHE_DIR / f"{key}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    logger.info(f"Cache saved: {cache_file}")
