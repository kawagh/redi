import json
import mimetypes
import os

import requests

from redi.client import client
from redi.config import redmine_url
from redi.i18n import messages


def upload_file(file_path: str) -> dict:
    if not os.path.isfile(file_path):
        print(messages.file_not_found.format(path=file_path))
        exit(1)
    filename = os.path.basename(file_path)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        response = client.post(
            "/uploads.json",
            headers={"Content-Type": "application/octet-stream"},
            data=f,
        )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.file_upload_failed_with_path.format(path=file_path))
        exit(1)
    token = response.json()["upload"]["token"]
    return {
        "token": token,
        "filename": filename,
        "content_type": content_type,
    }


def fetch_attachment(attachment_id: str) -> dict:
    response = client.get(f"/attachments/{attachment_id}.json")
    if response.status_code == 404:
        print(messages.attachment_not_found.format(id=attachment_id))
        exit(1)
    response.raise_for_status()
    return response.json()["attachment"]


def read_attachment(attachment_id: str, full: bool = False) -> None:
    attachment = fetch_attachment(attachment_id)
    if full:
        print(json.dumps(attachment, ensure_ascii=False))
        return
    lines = [
        f"{attachment['id']} {attachment['filename']}",
        messages.label_size.format(value=attachment.get("filesize", "")),
        messages.label_kind.format(value=attachment.get("content_type", "")),
    ]
    author = attachment.get("author") or {}
    if author:
        lines.append(messages.label_author.format(value=author.get("name", "")))
    if attachment.get("created_on"):
        lines.append(messages.label_created_on.format(value=attachment["created_on"]))
    if attachment.get("description"):
        lines.append(
            messages.label_description_field.format(value=attachment["description"])
        )
    if attachment.get("content_url"):
        lines.append(messages.label_url_field.format(value=attachment["content_url"]))
    print("\n".join(lines))


def delete_attachment(attachment_id: str) -> None:
    response = client.delete(f"/attachments/{attachment_id}.json")
    if response.status_code == 404:
        print(messages.attachment_not_found.format(id=attachment_id))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.attachment_delete_failed)
        exit(1)
    print(messages.attachment_deleted.format(id=attachment_id))


def update_attachment(
    attachment_id: str,
    filename: str | None = None,
    description: str | None = None,
) -> None:
    data: dict = {}
    if filename is not None:
        data["filename"] = filename
    if description is not None:
        data["description"] = description
    if not data:
        print(messages.update_canceled)
        exit()
    response = client.patch(
        f"/attachments/{attachment_id}.json", json={"attachment": data}
    )
    if response.status_code == 404:
        print(messages.attachment_not_found.format(id=attachment_id))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.attachment_update_failed)
        exit(1)
    print(
        messages.attachment_updated.format(
            url=f"{redmine_url}/attachments/{attachment_id}"
        )
    )
