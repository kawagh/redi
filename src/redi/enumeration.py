import json

from redi import cache
from redi.client import client


def _fetch_enumeration(resource: str) -> list[dict]:
    cached = cache.load(resource)
    if cached is not None:
        return cached
    response = client.get(f"/enumerations/{resource}.json")
    response.raise_for_status()
    data = response.json()[resource]
    cache.save(resource, data)
    return data


def _list_enumeration(resource: str, full: bool = False) -> None:
    items = _fetch_enumeration(resource)
    if full:
        print(json.dumps(items, ensure_ascii=False))
    else:
        for item in items:
            print(f"{item['id']} {item['name']}")


def fetch_issue_priorities() -> list[dict]:
    return _fetch_enumeration("issue_priorities")


def list_issue_priorities(full: bool = False) -> None:
    _list_enumeration("issue_priorities", full)


def fetch_time_entry_activities() -> list[dict]:
    return _fetch_enumeration("time_entry_activities")


def list_time_entry_activities(full: bool = False) -> None:
    _list_enumeration("time_entry_activities", full)


def list_document_categories(full: bool = False) -> None:
    _list_enumeration("document_categories", full)
