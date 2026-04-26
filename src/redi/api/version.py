import json
import webbrowser

import requests

from redi.client import client
from redi.config import redmine_url
from redi.i18n import messages


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
        print(messages.version_create_failed)
        exit(1)
    created = response.json()["version"]
    print(
        messages.version_created.format(
            id=created["id"],
            name=created["name"],
            url=f"{redmine_url}/versions/{created['id']}",
        )
    )


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
    if due_date is not None:
        version_data["due_date"] = due_date
    if description is not None:
        version_data["description"] = description
    if sharing:
        version_data["sharing"] = sharing
    if len(version_data) == 0:
        print(messages.update_canceled)
        exit()
    response = client.put(
        f"/versions/{version_id}.json", json={"version": version_data}
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.version_update_failed)
        exit(1)
    print(
        messages.version_updated.format(
            id=version_id, url=f"{redmine_url}/versions/{version_id}"
        )
    )


def fetch_version(version_id: str) -> dict:
    response = client.get(f"/versions/{version_id}.json")
    if response.status_code == 404:
        print(messages.version_not_found.format(id=version_id))
        exit(1)
    response.raise_for_status()
    return response.json()["version"]


def read_version(version_id: str, full: bool = False, web: bool = False) -> None:
    if web:
        url = f"{redmine_url}/versions/{version_id}"
        print(url)
        webbrowser.open(url)
        return
    version = fetch_version(version_id)
    if full:
        print(json.dumps(version, ensure_ascii=False))
        return

    lines = []
    lines.append(
        f"{version['id']} {version['name']} ({version['status']}) {redmine_url}/versions/{version['id']}"
    )
    project = version.get("project")
    if project:
        lines.append(
            messages.label_project_field.format(
                id=project.get("id"), name=project.get("name", "")
            )
        )
    if version.get("due_date"):
        lines.append(messages.label_due_date_field.format(value=version["due_date"]))
    if version.get("sharing"):
        lines.append(messages.label_sharing_field.format(value=version["sharing"]))
    if version.get("description"):
        lines.append("")
        lines.append(version["description"])
    print("\n".join(lines))


def delete_version(version_id: str) -> None:
    response = client.delete(f"/versions/{version_id}.json")
    if response.status_code == 404:
        print(messages.version_not_found.format(id=version_id))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.version_delete_failed)
        exit(1)
    print(messages.version_deleted.format(id=version_id))


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
