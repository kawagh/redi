import json

import requests

from redi.api.attachment import upload_file
from redi.client import client
from redi.i18n import messages


def list_files(project_id: str, full: bool = False) -> None:
    response = client.get(f"/projects/{project_id}/files.json")
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        exit(1)
    response.raise_for_status()
    files = response.json()["files"]
    if full:
        print(json.dumps(files, ensure_ascii=False))
        return
    for f in files:
        version = f.get("version") or {}
        version_label = f" [{version.get('name')}]" if version else ""
        size = f.get("filesize", "")
        print(f"{f['id']} {f['filename']} ({size}B){version_label}")


def create_file(
    project_id: str,
    file_path: str,
    version_id: int | None = None,
    description: str | None = None,
) -> None:
    upload = upload_file(file_path)
    file_data: dict = {
        "token": upload["token"],
        "filename": upload["filename"],
        "content_type": upload["content_type"],
    }
    if version_id is not None:
        file_data["version_id"] = version_id
    if description is not None:
        file_data["description"] = description
    response = client.post(
        f"/projects/{project_id}/files.json", json={"file": file_data}
    )
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.file_upload_failed)
        exit(1)
    print(messages.file_uploaded.format(filename=upload["filename"]))
