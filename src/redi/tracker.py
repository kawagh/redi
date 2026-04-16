import json

from redi import cache
from redi.client import client

CACHE_KEY = "trackers"


def fetch_trackers() -> list[dict]:
    cached = cache.load(CACHE_KEY)
    if cached is not None:
        return cached
    response = client.get("/trackers.json")
    response.raise_for_status()
    data = response.json()["trackers"]
    cache.save(CACHE_KEY, data)
    return data


def list_trackers(full: bool = False) -> None:
    trackers = fetch_trackers()
    if full:
        print(json.dumps(trackers, ensure_ascii=False))
    else:
        for tracker in trackers:
            print(f"{tracker['id']} {tracker['name']}")
