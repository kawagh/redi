from typing import Literal

from redi import cache
from redi.client import client

# Redmine の /enumerations/{resource}.json で引ける列挙リソース。
# キャッシュキーとレスポンスのキーも同じ文字列を使う。
EnumerationResource = Literal[
    "issue_priorities", "time_entry_activities", "document_categories"
]


def _fetch_enumeration(
    resource: EnumerationResource, refresh: bool = False
) -> list[dict]:
    cached = None if refresh else cache.load(resource)
    if cached is not None:
        return cached
    response = client.get(f"/enumerations/{resource}.json")
    response.raise_for_status()
    data = response.json()[resource]
    cache.save(resource, data)
    return data


def fetch_issue_priorities(refresh: bool = False) -> list[dict]:
    """優先度一覧を返す。refresh=True ならキャッシュを読まず取り直す。"""
    return _fetch_enumeration("issue_priorities", refresh)


def fetch_time_entry_activities(refresh: bool = False) -> list[dict]:
    """作業分類一覧を返す。refresh=True ならキャッシュを読まず取り直す。"""
    return _fetch_enumeration("time_entry_activities", refresh)


def fetch_document_categories(refresh: bool = False) -> list[dict]:
    """文書カテゴリ一覧を返す。refresh=True ならキャッシュを読まず取り直す。"""
    return _fetch_enumeration("document_categories", refresh)
