import json
import webbrowser

import requests

from redi.client import client
from redi.config import redmine_url
from redi.i18n import messages


def list_projects(full: bool = False) -> None:
    projects = fetch_projects()
    if full:
        print(json.dumps(projects, ensure_ascii=False))
    else:
        for project in projects:
            print(f"{project['id']} {project['name']}")


def fetch_projects() -> list[dict]:
    response = client.get("/projects.json")
    response.raise_for_status()
    data = response.json()
    return data.get("projects", [])


def resolve_project_id(value: str) -> str:
    if str(value).isdigit():
        return str(value)
    projects = fetch_projects()
    for p in projects:
        if p.get("identifier") == value or p.get("name") == value:
            return str(p["id"])
    print(messages.project_not_found.format(id=value))
    exit(1)


def fetch_project(project_id: str, include: str = "") -> dict:
    params: dict = {}
    if include:
        params["include"] = include
    response = client.get(f"/projects/{project_id}.json", params=params)
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        exit(1)
    response.raise_for_status()
    return response.json()["project"]


def create_project(
    name: str,
    identifier: str,
    description: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    tracker_ids: list[int] | None = None,
) -> None:
    data: dict = {
        "name": name,
        "identifier": identifier,
    }
    if description is not None:
        data["description"] = description
    if is_public is not None:
        data["is_public"] = is_public
    if parent_id is not None:
        data["parent_id"] = parent_id
    if tracker_ids is not None:
        data["tracker_ids"] = tracker_ids
    try:
        response = client.post("/projects.json", json={"project": data})
        response.raise_for_status()
        project = response.json()["project"]
        print(f"{project['id']} {project['name']} ({project['identifier']})")
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        exit(1)


def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    tracker_ids: list[int] | None = None,
) -> None:
    data: dict = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if is_public is not None:
        data["is_public"] = is_public
    if parent_id is not None:
        data["parent_id"] = parent_id
    if tracker_ids is not None:
        data["tracker_ids"] = tracker_ids
    if len(data) == 0:
        print(messages.update_canceled)
        exit()
    response = client.put(f"/projects/{project_id}.json", json={"project": data})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.project_update_failed)
        exit(1)
    print(messages.project_updated.format(id=project_id))


def archive_project(project_id: str) -> None:
    response = client.put(f"/projects/{project_id}/archive.json")
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.project_archive_failed)
        exit(1)
    print(messages.project_archived.format(id=project_id))


def unarchive_project(project_id: str) -> None:
    response = client.put(f"/projects/{project_id}/unarchive.json")
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.project_unarchive_failed)
        exit(1)
    print(messages.project_unarchived.format(id=project_id))


def delete_project(project_id: str) -> None:
    response = client.delete(f"/projects/{project_id}.json")
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.project_delete_failed)
        exit(1)
    print(messages.project_deleted.format(id=project_id))


def read_project(
    project_id: str, include: str = "", full: bool = False, web: bool = False
) -> None:
    if web:
        url = f"{redmine_url}/projects/{project_id}"
        print(url)
        webbrowser.open(url)
        return
    params: dict = {}
    if include:
        params["include"] = include
    response = client.get(f"/projects/{project_id}.json", params=params)
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        exit(1)
    response.raise_for_status()
    project = response.json()["project"]
    if full:
        print(json.dumps(project, ensure_ascii=False))
        return

    lines = []
    lines.append(f"{project['id']} {project['name']} ({project['identifier']})")
    if project.get("description"):
        lines.append("")
        lines.append(project["description"])
    parent = project.get("parent")
    if parent:
        lines.append("")
        lines.append(f"親プロジェクト: {parent.get('id')} {parent.get('name', '')}")
    trackers = project.get("trackers") or []
    if trackers:
        lines.append("")
        lines.append("トラッカー:")
        for t in trackers:
            lines.append(f"  {t['id']} {t['name']}")
    issue_categories = project.get("issue_categories") or []
    if issue_categories:
        lines.append("")
        lines.append("イシューカテゴリ:")
        for c in issue_categories:
            lines.append(f"  {c['id']} {c['name']}")
    enabled_modules = project.get("enabled_modules") or []
    if enabled_modules:
        lines.append("")
        lines.append("有効モジュール:")
        for m in enabled_modules:
            lines.append(f"  {m.get('name')}")
    print("\n".join(lines))
