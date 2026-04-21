import json
import webbrowser

import requests

from redi.client import client
from redi.config import redmine_url


def list_projects(full: bool = False) -> None:
    response = client.get("/projects.json")
    projects = response.json()["projects"]
    if full:
        print(json.dumps(projects, ensure_ascii=False))
    else:
        for project in projects:
            print(f"{project['id']} {project['name']}")


def fetch_project(project_id: str, include: str = "") -> dict:
    params: dict = {}
    if include:
        params["include"] = include
    response = client.get(f"/projects/{project_id}.json", params=params)
    if response.status_code == 404:
        print(f"プロジェクトが見つかりません: {project_id}")
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
        print("更新をキャンセルしました")
        exit()
    response = client.put(f"/projects/{project_id}.json", json={"project": data})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("プロジェクトの更新に失敗しました")
        exit(1)
    print(f"プロジェクトを更新しました: {project_id}")


def archive_project(project_id: str) -> None:
    response = client.put(f"/projects/{project_id}/archive.json")
    if response.status_code == 404:
        print(f"プロジェクトが見つかりません: {project_id}")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("プロジェクトのアーカイブに失敗しました")
        exit(1)
    print(f"プロジェクトをアーカイブしました: {project_id}")


def unarchive_project(project_id: str) -> None:
    response = client.put(f"/projects/{project_id}/unarchive.json")
    if response.status_code == 404:
        print(f"プロジェクトが見つかりません: {project_id}")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("プロジェクトのアーカイブ解除に失敗しました")
        exit(1)
    print(f"プロジェクトのアーカイブを解除しました: {project_id}")


def delete_project(project_id: str) -> None:
    response = client.delete(f"/projects/{project_id}.json")
    if response.status_code == 404:
        print(f"プロジェクトが見つかりません: {project_id}")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("プロジェクトの削除に失敗しました")
        exit(1)
    print(f"プロジェクトを削除しました: {project_id}")


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
        print(f"プロジェクトが見つかりません: {project_id}")
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
