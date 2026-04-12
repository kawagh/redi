import json

import requests

from redi.config import redmine_api_key, redmine_url


def fetch_attachment(attachment_id: str) -> dict:
    response = requests.get(
        f"{redmine_url}/attachments/{attachment_id}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
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
