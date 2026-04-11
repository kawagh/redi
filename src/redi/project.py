import json

import requests

from redi.config import redmine_api_key, redmine_url


def list_projects(full: bool = False) -> None:
    response = requests.get(
        f"{redmine_url}/projects.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
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
        response = requests.post(
            f"{redmine_url}/projects.json",
            headers={
                "X-Redmine-API-Key": redmine_api_key,
                "Content-Type": "application/json",
            },
            json={"project": data},
        )
        response.raise_for_status()
        project = response.json()["project"]
        print(f"{project['id']} {project['name']} ({project['identifier']})")
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        exit(1)


def read_project(project_id: str, include: str = "") -> None:
    params: dict = {}
    if include:
        params["include"] = include
    response = requests.get(
        f"{redmine_url}/projects/{project_id}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
        params=params,
    )
    project = response.json()["project"]
    print(json.dumps(project, ensure_ascii=False, indent=2))
