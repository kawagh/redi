import json

import requests

from redi.config import redmine_api_key, redmine_url


def list_roles(full: bool = False) -> None:
    response = requests.get(
        f"{redmine_url}/roles.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    response.raise_for_status()
    roles = response.json()["roles"]
    if full:
        print(json.dumps(roles, ensure_ascii=False))
    else:
        for role in roles:
            print(f"{role['id']} {role['name']}")


def fetch_role(role_id: str) -> dict:
    response = requests.get(
        f"{redmine_url}/roles/{role_id}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    if response.status_code == 404:
        print(f"ロールが見つかりません: #{role_id}")
        exit(1)
    response.raise_for_status()
    return response.json()["role"]


def read_role(role_id: str, full: bool = False) -> None:
    role = fetch_role(role_id)
    if full:
        print(json.dumps(role, ensure_ascii=False))
        return
    lines = [f"{role['id']} {role['name']}"]
    if "assignable" in role:
        lines.append(f"割り当て可能: {role['assignable']}")
    if role.get("issues_visibility"):
        lines.append(f"チケットの表示: {role['issues_visibility']}")
    if role.get("time_entries_visibility"):
        lines.append(f"作業時間の表示: {role['time_entries_visibility']}")
    if role.get("users_visibility"):
        lines.append(f"ユーザーの表示: {role['users_visibility']}")
    permissions = role.get("permissions") or []
    if permissions:
        lines.append("権限:")
        for p in permissions:
            lines.append(f"  {p}")
    print("\n".join(lines))
