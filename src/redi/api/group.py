import json

from redi.client import client


def list_groups(full: bool = False) -> None:
    response = client.get("/groups.json")
    response.raise_for_status()
    groups = response.json()["groups"]
    if full:
        print(json.dumps(groups, ensure_ascii=False))
    else:
        for group in groups:
            print(f"{group['id']} {group['name']}")
