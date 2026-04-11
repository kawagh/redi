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
