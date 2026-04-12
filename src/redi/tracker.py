import json

import requests

from redi.config import redmine_api_key, redmine_url


def fetch_trackers() -> list[dict]:
    response = requests.get(
        f"{redmine_url}/trackers.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    response.raise_for_status()
    return response.json()["trackers"]


def list_trackers(full: bool = False) -> None:
    trackers = fetch_trackers()
    if full:
        print(json.dumps(trackers, ensure_ascii=False))
    else:
        for tracker in trackers:
            print(f"{tracker['id']} {tracker['name']}")
