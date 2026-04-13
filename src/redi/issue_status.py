import json

from redi.client import client


def fetch_issue_statuses() -> list[dict]:
    response = client.get("/issue_statuses.json")
    response.raise_for_status()
    return response.json()["issue_statuses"]


def list_issue_statuses(full: bool = False) -> None:
    issue_statuses = fetch_issue_statuses()
    if full:
        print(json.dumps(issue_statuses, ensure_ascii=False))
    else:
        for s in issue_statuses:
            print(f"{s['id']} {s['name']}")
