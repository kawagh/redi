import requests

from redi.config import redmine_api_key, redmine_url


def list_projects() -> None:
    response = requests.get(
        f"{redmine_url}/projects.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    projects = response.json()["projects"]
    for project in projects:
        print(project)


def read_project(project_id: str) -> None:
    response = requests.get(
        f"{redmine_url}/projects/{project_id}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    project = response.json()["project"]
    print(project)
