from redi import cache
from redi.client import client

CACHE_KEY = "issue_statuses"


def fetch_issue_statuses(refresh: bool = False) -> list[dict]:
    """ステータス一覧を返す。refresh=True ならキャッシュを読まず取り直す。"""
    cached = None if refresh else cache.load(CACHE_KEY)
    if cached is not None:
        return cached
    response = client.get("/issue_statuses.json")
    response.raise_for_status()
    data = response.json()["issue_statuses"]
    cache.save(CACHE_KEY, data)
    return data
