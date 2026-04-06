import os
import requests

redmine_url = os.environ.get("REDMINE_URL")
redmine_api_key = os.environ.get("REDMINE_API_KEY")

if not redmine_url:
    print("set REDMINE_URL")
    exit(1)
if not redmine_url:
    print("set REDMINE_API_KEY")
    exit(1)


def main() -> None:
    response = requests.get(
        f"{redmine_url}/projects.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    projects = response.json()["projects"]
    for project in projects:
        print(project)
