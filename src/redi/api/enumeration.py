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


def fetch_issue_priorities() -> list[dict]:
    return _fetch_enumeration("issue_priorities")


def fetch_time_entry_activities() -> list[dict]:
    return _fetch_enumeration("time_entry_activities")


def fetch_document_categories() -> list[dict]:
    return _fetch_enumeration("document_categories")
