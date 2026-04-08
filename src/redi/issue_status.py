import json

import requests

from redi.config import redmine_api_key, redmine_url


def list_issue_statuses(full: bool = False) -> None:
    response = requests.get(
        f"{redmine_url}/issue_statuses.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    response.raise_for_status()
    issue_statuses = response.json()["issue_statuses"]
    if full:
        print(json.dumps(issue_statuses, ensure_ascii=False))
    else:
        for s in issue_statuses:
            print(f"{s['id']} {s['name']}")
