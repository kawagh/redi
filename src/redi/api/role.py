import json

from redi.client import client
from redi.i18n import messages


def list_roles(full: bool = False) -> None:
    response = client.get("/roles.json")
    response.raise_for_status()
    roles = response.json()["roles"]
    if full:
        print(json.dumps(roles, ensure_ascii=False))
    else:
        for role in roles:
            print(f"{role['id']} {role['name']}")


def fetch_role(role_id: str) -> dict:
    response = client.get(f"/roles/{role_id}.json")
    if response.status_code == 404:
        print(messages.role_not_found.format(id=role_id))
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
        lines.append(messages.label_assignable.format(value=role["assignable"]))
    if role.get("issues_visibility"):
        lines.append(
            messages.label_issues_visibility.format(value=role["issues_visibility"])
        )
    if role.get("time_entries_visibility"):
        lines.append(
            messages.label_time_entries_visibility.format(
                value=role["time_entries_visibility"]
            )
        )
    if role.get("users_visibility"):
        lines.append(
            messages.label_users_visibility.format(value=role["users_visibility"])
        )
    permissions = role.get("permissions") or []
    if permissions:
        lines.append(messages.label_permissions_header)
        for p in permissions:
            lines.append(f"  {p}")
    print("\n".join(lines))
