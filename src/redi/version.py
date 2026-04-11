import json

import requests

from redi.config import redmine_api_key, redmine_url


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
