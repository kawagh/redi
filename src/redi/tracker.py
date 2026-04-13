import json

from redi.client import client


def fetch_trackers() -> list[dict]:
    response = client.get("/trackers.json")
    response.raise_for_status()
    return response.json()["trackers"]


def list_trackers(full: bool = False) -> None:
    trackers = fetch_trackers()
    if full:
        print(json.dumps(trackers, ensure_ascii=False))
    else:
        for tracker in trackers:
            print(f"{tracker['id']} {tracker['name']}")
