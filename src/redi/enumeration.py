import json

import requests

from redi.config import redmine_api_key, redmine_url


def _fetch_enumeration(resource: str) -> list[dict]:
    response = requests.get(
        f"{redmine_url}/enumerations/{resource}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    response.raise_for_status()
    return response.json()[resource]


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


def list_time_entry_activities(full: bool = False) -> None:
    _list_enumeration("time_entry_activities", full)


def list_document_categories(full: bool = False) -> None:
    _list_enumeration("document_categories", full)
