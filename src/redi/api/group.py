import json

import requests

from redi.client import client
from redi.config import redmine_url


def list_groups(full: bool = False) -> None:
    response = client.get("/groups.json")
    response.raise_for_status()
    groups = response.json()["groups"]
    if full:
        print(json.dumps(groups, ensure_ascii=False))
    else:
        for group in groups:
            print(f"{group['id']} {group['name']}")


def create_group(name: str, user_ids: list[int] | None = None) -> None:
    group_data: dict = {"name": name}
    if user_ids:
        group_data["user_ids"] = user_ids
    response = client.post("/groups.json", json={"group": group_data})
    if response.status_code == 403:
        print("グループの作成には管理者権限が必要です")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("グループの作成に失敗しました")
        exit(1)
    created = response.json()["group"]
    print(
        f"グループを作成しました: {created['id']} {created['name']} {redmine_url}/groups/{created['id']}"
    )
