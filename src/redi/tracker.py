import json

import requests

from redi.config import redmine_api_key, redmine_url


def list_trackers(full: bool = False) -> None:
    response = requests.get(
        f"{redmine_url}/trackers.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    trackers = response.json()["trackers"]
    if full:
        print(json.dumps(trackers, ensure_ascii=False))
    else:
        for tracker in trackers:
            print(f"{tracker['id']} {tracker['name']}")
