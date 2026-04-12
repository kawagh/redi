import json

import requests

from redi.config import redmine_api_key, redmine_url


def list_issues(
    project_id: str | None = None,
    fixed_version_id: str | None = None,
    assigned_to: str | None = None,
    full: bool = False,
) -> None:
    params = {}
    if project_id:
        params["project_id"] = project_id
    if fixed_version_id:
        params["fixed_version_id"] = fixed_version_id
    if assigned_to:
        params["assigned_to_id"] = assigned_to
    response = requests.get(
        f"{redmine_url}/issues.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
        params=params,
    )
    tickets = response.json()["issues"]
    if full:
        print(json.dumps(tickets, ensure_ascii=False))
    else:
        for ticket in tickets:
            print(f"{ticket['id']} {ticket['subject']}")


def fetch_issue(issue_id: str, include: str = "") -> dict:
    params = {}
    if include:
        params["include"] = include
    response = requests.get(
        f"{redmine_url}/issues/{issue_id}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
        params=params,
    )
    if response.status_code == 404:
        print(f"イシューが見つかりません: #{issue_id}")
        exit(1)
    response.raise_for_status()
    return response.json()["issue"]


def read_issue(issue_id: str, full: bool = False) -> None:
    includes = ["relations"]
    if full:
        includes.append("journals")
    ticket = fetch_issue(issue_id, include=",".join(includes))

    if full:
        print(json.dumps(ticket, ensure_ascii=False))
    else:
        lines = []
        lines.append(f"{ticket['id']} {ticket['subject']}")
        if ticket.get("description"):
            lines.append("")
            lines.append(ticket["description"])
        relations = ticket.get("relations") or []
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
    response = requests.post(
        f"{redmine_url}/issues.json",
        headers={
            "X-Redmine-API-Key": redmine_api_key,
            "Content-Type": "application/json",
        },
        json={"issue": issue_data},
    )
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
    if len(issue_data) == 0:
        print("更新をキャンセルしました")
        exit()
    response = requests.put(
        f"{redmine_url}/issues/{issue_id}.json",
        headers={
            "X-Redmine-API-Key": redmine_api_key,
            "Content-Type": "application/json",
        },
        json={"issue": issue_data},
    )
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
    response = requests.put(
        f"{redmine_url}/issues/{issue_id}.json",
        headers={
            "X-Redmine-API-Key": redmine_api_key,
            "Content-Type": "application/json",
        },
        json={"issue": {"notes": notes}},
    )
    response.raise_for_status()
    # コメント後にイシューのジャーナル(プロパティ変更履歴やコメント)を取得して最新のjournal IDを得る
    issue_response = requests.get(
        f"{redmine_url}/issues/{issue_id}.json?include=journals",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    issue_response.raise_for_status()
    journals = issue_response.json()["issue"].get("journals", [])
    if journals:
        note_number = len(journals)
        url = f"{redmine_url}/issues/{issue_id}#note-{note_number}"
    else:
        url = f"{redmine_url}/issues/{issue_id}"
    print(f"コメントを追加しました: {url}")
