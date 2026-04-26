import json

import requests

from redi.client import client
from redi.config import redmine_url
from redi.i18n import messages


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
        print(messages.group_not_found.format(id=group_id))
        exit(1)
    if response.status_code == 403:
        print(messages.group_get_admin_required)
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
        print(messages.update_canceled)
        exit()
    response = client.put(f"/groups/{group_id}.json", json={"group": data})
    if response.status_code == 404:
        print(messages.group_not_found.format(id=group_id))
        exit(1)
    if response.status_code == 403:
        print(messages.group_update_admin_required)
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.group_update_failed)
        exit(1)
    print(messages.group_updated.format(id=group_id))


def add_group_user(group_id: str, user_id: int) -> None:
    response = client.post(
        f"/groups/{group_id}/users.json",
        json={"user_id": user_id},
    )
    if response.status_code == 404:
        print(messages.group_not_found.format(id=group_id))
        exit(1)
    if response.status_code == 403:
        print(messages.group_add_user_admin_required)
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.group_add_user_failed)
        exit(1)
    print(messages.group_user_added.format(group_id=group_id, user_id=user_id))


def remove_group_user(group_id: str, user_id: int) -> None:
    response = client.delete(f"/groups/{group_id}/users/{user_id}.json")
    if response.status_code == 404:
        print(
            messages.group_or_user_not_found.format(group_id=group_id, user_id=user_id)
        )
        exit(1)
    if response.status_code == 403:
        print(messages.group_remove_user_admin_required)
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.group_remove_user_failed)
        exit(1)
    print(messages.group_user_removed.format(group_id=group_id, user_id=user_id))


def delete_group(group_id: str) -> None:
    response = client.delete(f"/groups/{group_id}.json")
    if response.status_code == 404:
        print(messages.group_not_found.format(id=group_id))
        exit(1)
    if response.status_code == 403:
        print(messages.group_delete_admin_required)
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.group_delete_failed)
        exit(1)
    print(messages.group_deleted.format(id=group_id))


def create_group(name: str, user_ids: list[int] | None = None) -> None:
    group_data: dict = {"name": name}
    if user_ids:
        group_data["user_ids"] = user_ids
    response = client.post("/groups.json", json={"group": group_data})
    if response.status_code == 403:
        print(messages.group_create_admin_required)
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.group_create_failed)
        exit(1)
    created = response.json()["group"]
    print(
        messages.group_created.format(
            id=created["id"],
            name=created["name"],
            url=f"{redmine_url}/groups/{created['id']}",
        )
    )
