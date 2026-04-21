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


def fetch_group(group_id: str, include: str = "") -> dict:
    params: dict = {}
    if include:
        params["include"] = include
    response = client.get(f"/groups/{group_id}.json", params=params)
    if response.status_code == 404:
        print(f"グループが見つかりません: #{group_id}")
        exit(1)
    if response.status_code == 403:
        print("グループの取得には管理者権限が必要です")
        exit(1)
    response.raise_for_status()
    return response.json()["group"]


def read_group(group_id: str, full: bool = False) -> None:
    group = fetch_group(group_id, include="users,memberships")
    if full:
        print(json.dumps(group, ensure_ascii=False))
        return
    lines = [f"{group['id']} {group['name']}"]
    users = group.get("users") or []
    if users:
        lines.append("")
        lines.append("ユーザー:")
        for u in users:
            lines.append(f"  {u['id']} {u['name']}")
    memberships = group.get("memberships") or []
    if memberships:
        lines.append("")
        lines.append("メンバーシップ:")
        for m in memberships:
            project = m.get("project") or {}
            roles = m.get("roles") or []
            role_names = ", ".join(r.get("name", "") for r in roles)
            lines.append(
                f"  {project.get('id')} {project.get('name', '')} [{role_names}]"
            )
    print("\n".join(lines))


def update_group(
    group_id: str,
    name: str | None = None,
    user_ids: list[int] | None = None,
) -> None:
    data: dict = {}
    if name is not None:
        data["name"] = name
    if user_ids is not None:
        data["user_ids"] = user_ids
    if len(data) == 0:
        print("更新をキャンセルしました")
        exit()
    response = client.put(f"/groups/{group_id}.json", json={"group": data})
    if response.status_code == 404:
        print(f"グループが見つかりません: #{group_id}")
        exit(1)
    if response.status_code == 403:
        print("グループの更新には管理者権限が必要です")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("グループの更新に失敗しました")
        exit(1)
    print(f"グループを更新しました: {group_id}")


def add_group_user(group_id: str, user_id: int) -> None:
    response = client.post(
        f"/groups/{group_id}/users.json",
        json={"user_id": user_id},
    )
    if response.status_code == 404:
        print(f"グループが見つかりません: #{group_id}")
        exit(1)
    if response.status_code == 403:
        print("グループへのユーザー追加には管理者権限が必要です")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("グループへのユーザー追加に失敗しました")
        exit(1)
    print(f"グループ {group_id} にユーザー {user_id} を追加しました")


def remove_group_user(group_id: str, user_id: int) -> None:
    response = client.delete(f"/groups/{group_id}/users/{user_id}.json")
    if response.status_code == 404:
        print(f"グループまたはユーザーが見つかりません: #{group_id} / #{user_id}")
        exit(1)
    if response.status_code == 403:
        print("グループからのユーザー削除には管理者権限が必要です")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("グループからのユーザー削除に失敗しました")
        exit(1)
    print(f"グループ {group_id} からユーザー {user_id} を削除しました")


def delete_group(group_id: str) -> None:
    response = client.delete(f"/groups/{group_id}.json")
    if response.status_code == 404:
        print(f"グループが見つかりません: #{group_id}")
        exit(1)
    if response.status_code == 403:
        print("グループの削除には管理者権限が必要です")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("グループの削除に失敗しました")
        exit(1)
    print(f"グループを削除しました: {group_id}")


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
