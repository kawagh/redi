import json

import requests

from redi.api.project import resolve_project_id
from redi.client import client
from redi.i18n import messages


def create_time_entry(
    issue_id: str | None = None,
    project_id: str | None = None,
    hours: float = 0,
    activity_id: str | None = None,
    spent_on: str | None = None,
    comments: str | None = None,
) -> None:
    if not issue_id and not project_id:
        print(messages.issue_or_project_id_required)
        exit(1)
    # time_entries は他の API と異なり project_id に slug を受け付けず整数のみ許容
    # https://www.redmine.org/projects/redmine/wiki/Rest_TimeEntries
    if project_id is not None:
        project_id = resolve_project_id(project_id)
    data: dict = {"hours": hours}
    if issue_id:
        data["issue_id"] = issue_id
    if project_id:
        data["project_id"] = project_id
    if activity_id:
        data["activity_id"] = activity_id
    if spent_on:
        data["spent_on"] = spent_on
    if comments:
        data["comments"] = comments
    response = client.post("/time_entries.json", json={"time_entry": data})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.time_entry_create_failed)
        exit(1)
    created = response.json()["time_entry"]
    print(
        messages.time_entry_created.format(
            id=created["id"], hours=created["hours"], spent_on=created["spent_on"]
        )
    )


COMMENT_PREVIEW_MAX_LEN = 30


def format_time_entry_line(
    te: dict,
    include_user: bool = True,
    issue_subjects: dict[int, str] | None = None,
) -> str:
    # 列順: id / 日付 / 人 / 時間 / チケット(またはプロジェクト名) / コメント
    parts = [str(te["id"]), f"({te['spent_on']})"]
    if include_user:
        user = te.get("user") or {}
        name = user.get("name")
        if name:
            parts.append(name)
    parts.append(f"{te['hours']}h")
    issue = te.get("issue") or {}
    issue_id = issue.get("id")
    if issue_id:
        subject = (issue_subjects or {}).get(issue_id)
        parts.append(f"#{issue_id} {subject}" if subject else f"#{issue_id}")
    else:
        project = te.get("project") or {}
        project_name = project.get("name")
        if project_name:
            parts.append(project_name)
    comments = te.get("comments")
    if comments:
        preview = comments.strip().split("\n", 1)[0]
        if len(preview) > COMMENT_PREVIEW_MAX_LEN:
            preview = preview[:COMMENT_PREVIEW_MAX_LEN] + "…"
        parts.append(preview)
    return "  ".join(parts)


def fetch_issue_subjects(issue_ids: list[int]) -> dict[int, str]:
    if not issue_ids:
        return {}
    response = client.get(
        "/issues.json",
        params={"issue_id": ",".join(str(i) for i in issue_ids)},
    )
    response.raise_for_status()
    return {issue["id"]: issue["subject"] for issue in response.json()["issues"]}


def list_time_entries(
    project_id: str | None = None,
    user_id: str | None = None,
    full: bool = False,
) -> None:
    if project_id:
        path = f"/projects/{project_id}/time_entries.json"
    else:
        path = "/time_entries.json"
    params = {}
    if user_id:
        params["user_id"] = user_id
    response = client.get(path, params=params)
    response.raise_for_status()
    time_entries = response.json()["time_entries"]
    if full:
        print(json.dumps(time_entries, ensure_ascii=False))
        return
    include_user = user_id is None
    issue_ids = sorted(
        {
            te["issue"]["id"]
            for te in time_entries
            if te.get("issue") and te["issue"].get("id")
        }
    )
    issue_subjects = fetch_issue_subjects(issue_ids)
    for te in time_entries:
        print(
            format_time_entry_line(
                te,
                include_user=include_user,
                issue_subjects=issue_subjects,
            )
        )


def fetch_time_entry(time_entry_id: str) -> dict:
    response = client.get(f"/time_entries/{time_entry_id}.json")
    if response.status_code == 404:
        print(messages.time_entry_not_found.format(id=time_entry_id))
        exit(1)
    response.raise_for_status()
    return response.json()["time_entry"]


def read_time_entry(time_entry_id: str, full: bool = False) -> None:
    te = fetch_time_entry(time_entry_id)
    if full:
        print(json.dumps(te, ensure_ascii=False))
        return
    lines = [
        f"{te['id']} {te['hours']}h {te['activity']['name']} ({te['spent_on']})",
        f"  プロジェクト: {te['project']['name']} (id={te['project']['id']})",
        f"  ユーザー: {te['user']['name']} (id={te['user']['id']})",
    ]
    issue = te.get("issue")
    if issue:
        lines.append(f"  イシュー: #{issue['id']}")
    comments = te.get("comments")
    if comments:
        lines.append(f"  コメント: {comments}")
    print("\n".join(lines))


def update_time_entry(
    time_entry_id: str,
    hours: float | None = None,
    issue_id: str | None = None,
    project_id: str | None = None,
    activity_id: str | None = None,
    spent_on: str | None = None,
    comments: str | None = None,
) -> None:
    # time_entries は他の API と異なり project_id に slug を受け付けず整数のみ許容
    # https://www.redmine.org/projects/redmine/wiki/Rest_TimeEntries
    if project_id is not None:
        project_id = resolve_project_id(project_id)
    data: dict = {}
    if hours is not None:
        data["hours"] = hours
    if issue_id:
        data["issue_id"] = issue_id
    if project_id:
        data["project_id"] = project_id
    if activity_id:
        data["activity_id"] = activity_id
    if spent_on:
        data["spent_on"] = spent_on
    if comments is not None:
        data["comments"] = comments
    if not data:
        print(messages.update_canceled_no_changes)
        exit(1)
    response = client.put(
        f"/time_entries/{time_entry_id}.json", json={"time_entry": data}
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.time_entry_update_failed)
        exit(1)
    print(messages.time_entry_updated.format(id=time_entry_id))


def delete_time_entry(time_entry_id: str) -> None:
    response = client.delete(f"/time_entries/{time_entry_id}.json")
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.time_entry_delete_failed)
        exit(1)
    print(messages.time_entry_deleted.format(id=time_entry_id))
