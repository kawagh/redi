import json

import requests

from redi.attachment import upload_file
from redi.client import client
from redi.config import redmine_url


def list_issues(
    project_id: str | None = None,
    fixed_version_id: str | None = None,
    assigned_to: str | None = None,
    status_id: str | None = None,
    tracker_id: str | None = None,
    priority_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    full: bool = False,
) -> None:
    params: dict = {}
    if project_id:
        params["project_id"] = project_id
    if fixed_version_id:
        params["fixed_version_id"] = fixed_version_id
    if assigned_to:
        params["assigned_to_id"] = assigned_to
    if status_id:
        params["status_id"] = status_id
    if tracker_id:
        params["tracker_id"] = tracker_id
    if priority_id:
        params["priority_id"] = priority_id
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    response = client.get("/issues.json", params=params)
    issues = response.json()["issues"]
    if full:
        print(json.dumps(issues, ensure_ascii=False))
    else:
        for issue in issues:
            print(
                f"{issue['id']} {issue['subject']} {redmine_url}/issues/{issue['id']}"
            )


def fetch_issue(issue_id: str, include: str = "") -> dict:
    params = {}
    if include:
        params["include"] = include
    response = client.get(f"/issues/{issue_id}.json", params=params)
    if response.status_code == 404:
        print(f"イシューが見つかりません: #{issue_id}")
        exit(1)
    response.raise_for_status()
    return response.json()["issue"]


def read_issue(issue_id: str, full: bool = False) -> None:
    includes = ["relations", "attachments"]
    if full:
        includes.append("journals")
    issue = fetch_issue(issue_id, include=",".join(includes))

    if full:
        print(json.dumps(issue, ensure_ascii=False))
    else:
        lines = []
        lines.append(f"{issue['id']} {issue['subject']}")
        if issue.get("description"):
            lines.append("")
            lines.append(issue["description"])
        relations = issue.get("relations") or []
        if relations:
            lines.append("")
            lines.append("関係性:")
            target_id = int(issue_id)
            inverse_relation = {
                "precedes": "follows",
                "follows": "precedes",
                "blocks": "blocked",
                "blocked": "blocks",
                "duplicates": "duplicated",
                "duplicated": "duplicates",
                "copied_to": "copied_from",
                "copied_from": "copied_to",
                "relates": "relates",
            }
            relation_labels = {
                "relates": "関連している",
                "duplicates": "重複している",
                "duplicated": "重複されている",
                "blocks": "ブロック先",
                "blocked": "ブロック元",
                "precedes": "先行する",
                "follows": "後続する",
                "copied_to": "コピー先",
                "copied_from": "コピー元",
            }
            for r in relations:
                if r["issue_id"] == target_id:
                    other = r["issue_to_id"]
                    rel_type = r["relation_type"]
                else:
                    other = r["issue_id"]
                    rel_type = inverse_relation.get(
                        r["relation_type"], r["relation_type"]
                    )
                if isinstance(rel_type, str):
                    label = relation_labels.get(rel_type)
                else:
                    # unknown rel_type
                    label = rel_type
                lines.append(f"  [{label}] {redmine_url}/issues/{other}")
        attachments = issue.get("attachments") or []
        if attachments:
            lines.append("")
            lines.append("添付ファイル:")
            for a in attachments:
                lines.append(f"  {a['filename']} {a.get('content_url', '')}")

        print("\n".join(lines))


def parse_custom_fields(custom_fields_str: str) -> list[dict]:
    result = []
    for pair in custom_fields_str.split(","):
        key, _, value = pair.partition("=")
        if key:
            result.append({"id": int(key.strip()), "value": value.strip()})
    return result


def create_issue(
    project_id: str,
    subject: str,
    description: str = "",
    tracker_id: str | None = None,
    priority_id: str | None = None,
    assigned_to_id: str | None = None,
    custom_fields: str | None = None,
) -> None:
    issue_data: dict = {
        "project_id": project_id,
        "subject": subject,
    }
    if description:
        issue_data["description"] = description
    if tracker_id:
        issue_data["tracker_id"] = tracker_id
    if priority_id:
        issue_data["priority_id"] = priority_id
    if assigned_to_id:
        issue_data["assigned_to_id"] = assigned_to_id
    if custom_fields:
        issue_data["custom_fields"] = parse_custom_fields(custom_fields)
    response = client.post("/issues.json", json={"issue": issue_data})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("イシューの作成に失敗しました")
        exit(1)
    created = response.json()["issue"]
    url = f"{redmine_url}/issues/{created['id']}"
    print(f"イシューを作成しました: {url}")


def update_issue(
    issue_id: str,
    subject: str | None = None,
    description: str | None = None,
    tracker_id: str | None = None,
    status_id: str | None = None,
    priority_id: str | None = None,
    assigned_to_id: str | None = None,
    fixed_version_id: str | None = None,
    parent_issue_id: str | None = None,
    notes: str = "",
    custom_fields: str | None = None,
    attachments: list[str] = [],
) -> None:
    issue_data: dict = {}
    if subject:
        issue_data["subject"] = subject
    if description is not None:
        issue_data["description"] = description
    if tracker_id:
        issue_data["tracker_id"] = tracker_id
    if status_id:
        issue_data["status_id"] = status_id
    if priority_id:
        issue_data["priority_id"] = priority_id
    if assigned_to_id:
        issue_data["assigned_to_id"] = assigned_to_id
    if fixed_version_id:
        issue_data["fixed_version_id"] = fixed_version_id
    if parent_issue_id is not None:
        issue_data["parent_issue_id"] = parent_issue_id
    if notes:
        issue_data["notes"] = notes
    if custom_fields:
        issue_data["custom_fields"] = parse_custom_fields(custom_fields)
    if attachments:
        issue_data["uploads"] = [upload_file(file_path) for file_path in attachments]
    if len(issue_data) == 0:
        print("更新をキャンセルしました")
        exit()
    response = client.put(f"/issues/{issue_id}.json", json={"issue": issue_data})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("イシューの更新に失敗しました")
        exit(1)
    url = f"{redmine_url}/issues/{issue_id}"
    print(f"イシューを更新しました: {url}")


def add_note(issue_id: str, notes: str) -> None:
    response = client.put(f"/issues/{issue_id}.json", json={"issue": {"notes": notes}})
    response.raise_for_status()
    # コメント後にイシューのジャーナル(プロパティ変更履歴やコメント)を取得して最新のjournal IDを得る
    issue_response = client.get(f"/issues/{issue_id}.json?include=journals")
    issue_response.raise_for_status()
    journals = issue_response.json()["issue"].get("journals", [])
    if journals:
        note_number = len(journals)
        url = f"{redmine_url}/issues/{issue_id}#note-{note_number}"
    else:
        url = f"{redmine_url}/issues/{issue_id}"
    print(f"コメントを追加しました: {url}")
