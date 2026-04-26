import json
import webbrowser

import requests

from redi.api.attachment import upload_file
from redi.client import client
from redi.config import redmine_url
from redi.i18n import messages


def fetch_issues_page(
    project_id: str | None = None,
    fixed_version_id: str | None = None,
    assigned_to: str | None = None,
    status_id: str | None = None,
    tracker_id: str | None = None,
    priority_id: str | None = None,
    query_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> dict:
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
    if query_id:
        params["query_id"] = query_id
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    response = client.get("/issues.json", params=params)
    response.raise_for_status()
    return response.json()


def fetch_issues(
    project_id: str | None = None,
    fixed_version_id: str | None = None,
    assigned_to: str | None = None,
    status_id: str | None = None,
    tracker_id: str | None = None,
    priority_id: str | None = None,
    query_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict]:
    return fetch_issues_page(
        project_id=project_id,
        fixed_version_id=fixed_version_id,
        assigned_to=assigned_to,
        status_id=status_id,
        tracker_id=tracker_id,
        priority_id=priority_id,
        query_id=query_id,
        limit=limit,
        offset=offset,
    )["issues"]


def list_issues(
    project_id: str | None = None,
    fixed_version_id: str | None = None,
    assigned_to: str | None = None,
    status_id: str | None = None,
    tracker_id: str | None = None,
    priority_id: str | None = None,
    query_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    full: bool = False,
) -> None:
    issues = fetch_issues(
        project_id=project_id,
        fixed_version_id=fixed_version_id,
        assigned_to=assigned_to,
        status_id=status_id,
        tracker_id=tracker_id,
        priority_id=priority_id,
        query_id=query_id,
        limit=limit,
        offset=offset,
    )
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
        print(messages.issue_not_found.format(id=issue_id))
        exit(1)
    response.raise_for_status()
    return response.json()["issue"]


def read_issue(
    issue_id: str, include: str = "", full: bool = False, web: bool = False
) -> None:
    if web:
        url = f"{redmine_url}/issues/{issue_id}"
        print(url)
        webbrowser.open(url)
        return
    includes = ["relations", "attachments"]
    if full:
        includes.append("journals")
    if include:
        for name in include.split(","):
            name = name.strip()
            if name and name not in includes:
                includes.append(name)
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
            lines.append(messages.label_relations_header)
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
                "relates": messages.relation_label_relates,
                "duplicates": messages.relation_label_duplicates,
                "duplicated": messages.relation_label_duplicated,
                "blocks": messages.relation_label_blocks,
                "blocked": messages.relation_label_blocked,
                "precedes": messages.relation_label_precedes,
                "follows": messages.relation_label_follows,
                "copied_to": messages.relation_label_copied_to,
                "copied_from": messages.relation_label_copied_from,
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
            lines.append(messages.label_attachments_header)
            for a in attachments:
                lines.append(f"  {a['filename']} {a.get('content_url', '')}")
        children = issue.get("children") or []
        if children:
            lines.append("")
            lines.append(messages.label_children_header)
            for c in children:
                lines.append(f"  #{c['id']} {c.get('subject', '')}")
        watchers = issue.get("watchers") or []
        if watchers:
            lines.append("")
            lines.append(messages.label_watchers_header)
            for w in watchers:
                lines.append(f"  {w.get('name', w.get('id', ''))}")
        allowed_statuses = issue.get("allowed_statuses") or []
        if allowed_statuses:
            lines.append("")
            lines.append(messages.label_allowed_statuses_header)
            for s in allowed_statuses:
                lines.append(f"  {s.get('id')} {s.get('name')}")
        changesets = issue.get("changesets") or []
        if changesets:
            lines.append("")
            lines.append(messages.label_revisions_header)
            for c in changesets:
                lines.append(
                    f"  {c.get('revision', '')} {c.get('comments', '')}".rstrip()
                )
        journals = issue.get("journals") or []
        if journals:
            lines.append("")
            lines.append(messages.label_journals_header)
            for j in journals:
                author = (j.get("user") or {}).get("name", "")
                created = j.get("created_on", "")
                lines.append(f"  [{created}] {author}")
                for d in j.get("details") or []:
                    name = d.get("name", "")
                    old = d.get("old_value", "")
                    new = d.get("new_value", "")
                    lines.append(f"    {name}: {old} → {new}")
                notes = j.get("notes") or ""
                for nl in notes.splitlines():
                    lines.append(f"    {nl}")

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
        print(messages.issue_create_failed)
        exit(1)
    created = response.json()["issue"]
    url = f"{redmine_url}/issues/{created['id']}"
    print(messages.issue_created.format(url=url))


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
    start_date: str | None = None,
    due_date: str | None = None,
    done_ratio: int | None = None,
    estimated_hours: float | None = None,
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
    if assigned_to_id is not None:
        issue_data["assigned_to_id"] = assigned_to_id
    if fixed_version_id:
        issue_data["fixed_version_id"] = fixed_version_id
    if parent_issue_id is not None:
        issue_data["parent_issue_id"] = parent_issue_id
    if start_date is not None:
        issue_data["start_date"] = start_date
    if due_date is not None:
        issue_data["due_date"] = due_date
    if done_ratio is not None:
        issue_data["done_ratio"] = done_ratio
    if estimated_hours is not None:
        issue_data["estimated_hours"] = estimated_hours
    if notes:
        issue_data["notes"] = notes
    if custom_fields:
        issue_data["custom_fields"] = parse_custom_fields(custom_fields)
    if attachments:
        issue_data["uploads"] = [upload_file(file_path) for file_path in attachments]
    if len(issue_data) == 0:
        print(messages.update_canceled)
        exit()
    response = client.put(f"/issues/{issue_id}.json", json={"issue": issue_data})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.issue_update_failed)
        exit(1)
    url = f"{redmine_url}/issues/{issue_id}"
    print(messages.issue_updated.format(url=url))


def add_watcher(issue_id: str, user_id: int) -> None:
    response = client.post(
        f"/issues/{issue_id}/watchers.json",
        json={"user_id": user_id},
    )
    if response.status_code == 404:
        print(messages.issue_not_found.format(id=issue_id))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.watcher_add_failed)
        exit(1)
    print(messages.watcher_added.format(issue_id=issue_id, user_id=user_id))


def remove_watcher(issue_id: str, user_id: int) -> None:
    response = client.delete(f"/issues/{issue_id}/watchers/{user_id}.json")
    if response.status_code == 404:
        print(
            messages.issue_or_user_not_found.format(issue_id=issue_id, user_id=user_id)
        )
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.watcher_remove_failed)
        exit(1)
    print(messages.watcher_removed.format(issue_id=issue_id, user_id=user_id))


def delete_issue(issue_id: str) -> None:
    response = client.delete(f"/issues/{issue_id}.json")
    if response.status_code == 404:
        print(messages.issue_not_found.format(id=issue_id))
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.issue_delete_failed)
        exit(1)
    print(messages.issue_deleted.format(id=issue_id))


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
    print(messages.comment_added.format(url=url))
