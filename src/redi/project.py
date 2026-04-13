import json

import requests

from redi.client import client


def list_projects(full: bool = False) -> None:
    response = client.get("/projects.json")
    projects = response.json()["projects"]
    if full:
        print(json.dumps(projects, ensure_ascii=False))
    else:
        for project in projects:
            print(f"{project['id']} {project['name']}")


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


def read_project(project_id: str, include: str = "") -> None:
    params: dict = {}
    if include:
        params["include"] = include
    response = client.get(f"/projects/{project_id}.json", params=params)
    if response.status_code == 404:
        print(f"プロジェクトが見つかりません: {project_id}")
        exit(1)
    response.raise_for_status()
    project = response.json()["project"]
    print(json.dumps(project, ensure_ascii=False, indent=2))
