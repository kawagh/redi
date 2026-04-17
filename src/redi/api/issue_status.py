import json

from redi import cache
from redi.client import client

CACHE_KEY = "issue_statuses"


def fetch_issue_statuses() -> list[dict]:
    cached = cache.load(CACHE_KEY)
    if cached is not None:
        return cached
    response = client.get("/issue_statuses.json")
    response.raise_for_status()
    data = response.json()["issue_statuses"]
    cache.save(CACHE_KEY, data)
    return data


def list_issue_statuses(full: bool = False) -> None:
    issue_statuses = fetch_issue_statuses()
    if full:
        print(json.dumps(issue_statuses, ensure_ascii=False))
    else:
        for s in issue_statuses:
            print(f"{s['id']} {s['name']}")
