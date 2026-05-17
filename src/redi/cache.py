import json
import time
from pathlib import Path
from urllib.parse import urlsplit

CACHE_DIR = Path.home() / ".cache" / "redi"
# キャッシュの生存時間[s]
DEFAULT_TTL = 100 * 12 * 30 * 24 * 60 * 60  # 100 years


def _slugify_url(url: str) -> str:
    """redmineのURL をディレクトリ名に変換する

    https://redmine.example.com → redmine.example.com_8080_sub
    http://localhost:3000 → localhost_3000
    http://redmine.example.com:8080/sub → redmine.example.com_8080_sub
    """
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    port = f"{parsed.port}" if parsed.port else ""
    path = parsed.path.rstrip("/").lstrip("/").replace("/", "_")
    return "_".join(filter(None, [host, port, path]))


def _cache_path(key: str) -> Path:
    from redi import config

    return CACHE_DIR / _slugify_url(config.redmine_url) / f"{key}.json"


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
    path = _cache_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"timestamp": time.time(), "value": value}
    path.write_text(json.dumps(data, ensure_ascii=False))
