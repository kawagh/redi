from redi import cache
from redi.client import client

CACHE_KEY = "trackers"


def fetch_trackers(refresh: bool = False) -> list[dict]:
    """トラッカー一覧を返す。refresh=True ならキャッシュを読まず取り直す。"""
    cached = None if refresh else cache.load(CACHE_KEY)
    if cached is not None:
        return cached
    response = client.get("/trackers.json")
    response.raise_for_status()
    data = response.json()["trackers"]
    cache.save(CACHE_KEY, data)
    return data
