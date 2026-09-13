from typing import NotRequired, TypedDict, cast

from redi.api import cache
from redi.api.client import client
from redi.api.types import IdName

CACHE_KEY = "trackers"


class Tracker(TypedDict):
    """トラッカー。GET /trackers.json で返るフィールドを記載。"""

    id: int
    name: str
    default_status: NotRequired[IdName]
    description: NotRequired[str | None]


def fetch_trackers(refresh: bool = False) -> list[Tracker]:
    """トラッカー一覧を返す。refresh=True ならキャッシュを読まず取り直す。"""
    cached = None if refresh else cache.load(CACHE_KEY)
    if cached is not None:
        return cast(list[Tracker], cached)
    response = client.get("/trackers.json")
    response.raise_for_status()
    data = response.json()["trackers"]
    cache.save(CACHE_KEY, data)
    return cast(list[Tracker], data)
