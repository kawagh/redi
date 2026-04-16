import json
import time
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "redi"
# キャッシュの生存時間[s]
DEFAULT_TTL = 100 * 12 * 30 * 24 * 60 * 60  # 100 years


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def load(key: str, ttl: int = DEFAULT_TTL) -> list[dict] | None:
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        if time.time() - data["timestamp"] > ttl:
            return None
        return data["value"]
    except (json.JSONDecodeError, KeyError):
        return None


def save(key: str, value: list[dict]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data = {"timestamp": time.time(), "value": value}
    _cache_path(key).write_text(json.dumps(data, ensure_ascii=False))
