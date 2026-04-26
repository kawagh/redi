import json

import requests

from redi.client import client


def list_memberships(project_id: str, full: bool = False) -> None:
    response = client.get(f"/projects/{project_id}/memberships.json")
    response.raise_for_status()
    memberships = response.json()["memberships"]
    if full:
        print(json.dumps(memberships, ensure_ascii=False))
        return
    for m in memberships:
        print(_format_membership_line(m))


def fetch_project_users(project_id: str) -> list[dict]:
    """プロジェクトのメンバー（user）を返す。"""
    response = client.get(f"/projects/{project_id}/memberships.json")
    response.raise_for_status()
    memberships = response.json()["memberships"]
    return [m["user"] for m in memberships if m.get("user")]


def fetch_membership(membership_id: str) -> dict:
    response = client.get(f"/memberships/{membership_id}.json")
    if response.status_code == 404:
        print(f"メンバーシップが見つかりません: {membership_id}")
        exit(1)
    response.raise_for_status()
    return response.json()["membership"]


def read_membership(membership_id: str, full: bool = False) -> None:
    membership = fetch_membership(membership_id)
    if full:
        print(json.dumps(membership, ensure_ascii=False))
        return
    lines = [_format_membership_line(membership)]
    project = membership.get("project")
    if project:
        lines.append(f"プロジェクト: {project.get('id')} {project.get('name', '')}")
    roles = membership.get("roles") or []
    if roles:
        lines.append("ロール:")
        for r in roles:
            inherited = " (継承)" if r.get("inherited") else ""
            lines.append(f"  {r.get('id')} {r.get('name', '')}{inherited}")
    print("\n".join(lines))


def create_membership(
    project_id: str,
    role_ids: list[int],
    user_id: int | None = None,
    group_id: int | None = None,
) -> None:
    data: dict = {"role_ids": role_ids}
    if user_id is not None:
        data["user_id"] = user_id
    elif group_id is not None:
        data["user_id"] = group_id
    else:
        print("user_id または group_id を指定してください")
        exit(1)
    response = client.post(
        f"/projects/{project_id}/memberships.json", json={"membership": data}
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("メンバーシップの作成に失敗しました")
        exit(1)
    created = response.json()["membership"]
    print(f"メンバーシップを作成しました: {_format_membership_line(created)}")


def update_membership(membership_id: str, role_ids: list[int]) -> None:
    if not role_ids:
        print("更新をキャンセルしました")
        exit()
    response = client.put(
        f"/memberships/{membership_id}.json",
        json={"membership": {"role_ids": role_ids}},
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("メンバーシップの更新に失敗しました")
        exit(1)
    print(f"メンバーシップを更新しました: {membership_id}")


def delete_membership(membership_id: str) -> None:
    response = client.delete(f"/memberships/{membership_id}.json")
    if response.status_code == 404:
        print(f"メンバーシップが見つかりません: {membership_id}")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("メンバーシップの削除に失敗しました")
        exit(1)
    print(f"メンバーシップを削除しました: {membership_id}")


def _format_membership_line(membership: dict) -> str:
    principal = membership.get("user") or membership.get("group") or {}
    principal_kind = "user" if "user" in membership else "group"
    principal_str = f"{principal.get('id', '?')} {principal.get('name', '')}".strip()
    roles = membership.get("roles") or []
    role_str = ", ".join(r.get("name", "") for r in roles)
    return f"{membership['id']} [{principal_kind}] {principal_str} - {role_str}"
