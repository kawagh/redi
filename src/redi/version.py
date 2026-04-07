import requests

from redi.config import redmine_api_key, redmine_url


def list_versions(project_id: str) -> None:
    response = requests.get(
        f"{redmine_url}/projects/{project_id}/versions.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    versions = response.json()["versions"]
    for version in versions:
        print(f"{version['id']} {version['name']} ({version['status']})")
