import json

import requests

from redi.config import redmine_api_key, redmine_url


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
    response = requests.post(
        f"{redmine_url}/projects/{project_id}/versions.json",
        headers={
            "X-Redmine-API-Key": redmine_api_key,
            "Content-Type": "application/json",
        },
        json={"version": version_data},
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


def list_versions(project_id: str, full: bool = False) -> None:
    response = requests.get(
        f"{redmine_url}/projects/{project_id}/versions.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    versions = response.json()["versions"]
    if full:
        print(json.dumps(versions, ensure_ascii=False))
    else:
        for version in versions:
            print(f"{version['id']} {version['name']} ({version['status']})")
