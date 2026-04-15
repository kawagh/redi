import json
import webbrowser

import requests

from redi.client import client
from redi.config import redmine_url


def create_version(
    project_id: str,
    name: str,
    status: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
    sharing: str | None = None,
) -> None:
    version_data: dict = {"name": name}
    if status:
        version_data["status"] = status
    if due_date:
        version_data["due_date"] = due_date
    if description:
        version_data["description"] = description
    if sharing:
        version_data["sharing"] = sharing
    response = client.post(
        f"/projects/{project_id}/versions.json", json={"version": version_data}
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("バージョンの作成に失敗しました")
        exit(1)
    created = response.json()["version"]
    print(f"バージョンを作成しました: {created['id']} {created['name']}")


def update_version(
    version_id: str,
    name: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
    sharing: str | None = None,
) -> None:
    version_data: dict = {}
    if name:
        version_data["name"] = name
    if status:
        version_data["status"] = status
    if due_date:
        version_data["due_date"] = due_date
    if description:
        version_data["description"] = description
    if sharing:
        version_data["sharing"] = sharing
    if len(version_data) == 0:
        print("更新をキャンセルしました")
        exit()
    response = client.put(
        f"/versions/{version_id}.json", json={"version": version_data}
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("バージョンの更新に失敗しました")
        exit(1)
    print(f"バージョンを更新しました: {version_id}")


def read_version(version_id: str, full: bool = False, web: bool = False) -> None:
    if web:
        url = f"{redmine_url}/versions/{version_id}"
        print(url)
        webbrowser.open(url)
        return
    response = client.get(f"/versions/{version_id}.json")
    if response.status_code == 404:
        print(f"バージョンが見つかりません: {version_id}")
        exit(1)
    response.raise_for_status()
    version = response.json()["version"]
    if full:
        print(json.dumps(version, ensure_ascii=False))
        return

    lines = []
    lines.append(
        f"{version['id']} {version['name']} ({version['status']}) {redmine_url}/versions/{version['id']}"
    )
    project = version.get("project")
    if project:
        lines.append(f"プロジェクト: {project.get('id')} {project.get('name', '')}")
    if version.get("due_date"):
        lines.append(f"期日: {version['due_date']}")
    if version.get("sharing"):
        lines.append(f"共有: {version['sharing']}")
    if version.get("description"):
        lines.append("")
        lines.append(version["description"])
    print("\n".join(lines))


def fetch_versions(project_id: str) -> list[dict]:
    response = client.get(f"/projects/{project_id}/versions.json")
    response.raise_for_status()
    return response.json()["versions"]


def list_versions(project_id: str, full: bool = False) -> None:
    versions = fetch_versions(project_id)
    if full:
        print(json.dumps(versions, ensure_ascii=False))
    else:
        for version in versions:
            print(
                f"{version['id']} {version['name']} ({version['status']}) {redmine_url}/versions/{version['id']}"
            )
