import json
import mimetypes
import os

import requests

from redi.client import client
from redi.config import redmine_url


def upload_file(file_path: str) -> dict:
    if not os.path.isfile(file_path):
        print(f"ファイルが見つかりません: {file_path}")
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
        print(f"ファイルのアップロードに失敗しました: {file_path}")
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
        print(f"添付ファイルが見つかりません: #{attachment_id}")
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
        f"サイズ: {attachment.get('filesize', '')}",
        f"種別: {attachment.get('content_type', '')}",
    ]
    author = attachment.get("author") or {}
    if author:
        lines.append(f"作成者: {author.get('name', '')}")
    if attachment.get("created_on"):
        lines.append(f"作成日時: {attachment['created_on']}")
    if attachment.get("description"):
        lines.append(f"説明: {attachment['description']}")
    if attachment.get("content_url"):
        lines.append(f"URL: {attachment['content_url']}")
    print("\n".join(lines))


def delete_attachment(attachment_id: str) -> None:
    response = client.delete(f"/attachments/{attachment_id}.json")
    if response.status_code == 404:
        print(f"添付ファイルが見つかりません: #{attachment_id}")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("添付ファイルの削除に失敗しました")
        exit(1)
    print(f"添付ファイルを削除しました: #{attachment_id}")


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
        print("更新をキャンセルしました")
        exit()
    response = client.patch(
        f"/attachments/{attachment_id}.json", json={"attachment": data}
    )
    if response.status_code == 404:
        print(f"添付ファイルが見つかりません: #{attachment_id}")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("添付ファイルの更新に失敗しました")
        exit(1)
    print(f"添付ファイルを更新しました: {redmine_url}/attachments/{attachment_id}")
