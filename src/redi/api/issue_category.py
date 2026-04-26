import json

import requests

from redi.client import client
from redi.i18n import messages


def list_issue_categories(project_id: str, full: bool = False) -> None:
    response = client.get(f"/projects/{project_id}/issue_categories.json")
    response.raise_for_status()
    categories = response.json()["issue_categories"]
    if full:
        print(json.dumps(categories, ensure_ascii=False))
        return
    for category in categories:
        assigned = category.get("assigned_to") or {}
        assigned_label = (
            f" [{assigned.get('id')} {assigned.get('name', '')}]" if assigned else ""
        )
        print(f"{category['id']} {category['name']}{assigned_label}")


def fetch_issue_categories(project_id: str) -> list[dict]:
    response = client.get(f"/projects/{project_id}/issue_categories.json")
    response.raise_for_status()
    return response.json()["issue_categories"]


def fetch_issue_category(category_id: str) -> dict:
    response = client.get(f"/issue_categories/{category_id}.json")
    if response.status_code == 404:
        print(messages.category_not_found.format(id=category_id))
        exit(1)
    response.raise_for_status()
    return response.json()["issue_category"]


def read_issue_category(category_id: str, full: bool = False) -> None:
    category = fetch_issue_category(category_id)
    if full:
        print(json.dumps(category, ensure_ascii=False))
        return
    lines = [f"{category['id']} {category['name']}"]
    project = category.get("project") or {}
    if project:
        lines.append(
            messages.label_project_field.format(
                id=project.get("id"), name=project.get("name", "")
            )
        )
    assigned = category.get("assigned_to") or {}
    if assigned:
        lines.append(
            messages.label_default_assignee.format(
                id=assigned.get("id"), name=assigned.get("name", "")
            )
        )
    print("\n".join(lines))


def create_issue_category(
    project_id: str,
    name: str,
    assigned_to_id: int | None = None,
) -> None:
    data: dict = {"name": name}
    if assigned_to_id is not None:
        data["assigned_to_id"] = assigned_to_id
    response = client.post(
        f"/projects/{project_id}/issue_categories.json",
        json={"issue_category": data},
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.category_create_failed)
        exit(1)
    created = response.json()["issue_category"]
    print(messages.category_created.format(id=created["id"], name=created["name"]))


def update_issue_category(
    category_id: str,
    name: str | None = None,
    assigned_to_id: int | None = None,
) -> None:
    data: dict = {}
    if name is not None:
        data["name"] = name
    if assigned_to_id is not None:
        data["assigned_to_id"] = assigned_to_id
    if len(data) == 0:
        print(messages.update_canceled)
        exit()
    response = client.put(
        f"/issue_categories/{category_id}.json",
        json={"issue_category": data},
    )
    if response.status_code == 404:
        print(messages.category_not_found.format(id=category_id))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.category_update_failed)
        exit(1)
    print(messages.category_updated.format(id=category_id))


def delete_issue_category(category_id: str, reassign_to_id: int | None = None) -> None:
    params: dict = {}
    if reassign_to_id is not None:
        params["reassign_to_id"] = reassign_to_id
    response = client.delete(f"/issue_categories/{category_id}.json", params=params)
    if response.status_code == 404:
        print(messages.category_not_found.format(id=category_id))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.category_delete_failed)
        exit(1)
    print(messages.category_deleted.format(id=category_id))
