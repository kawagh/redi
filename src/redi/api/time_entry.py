from __future__ import annotations

import json
from typing import NotRequired, TypedDict, cast

import requests

from redi.api.exceptions import RedmineValidationException, print_http_error_body
from redi.api.project import resolve_project_id
from redi.api.types import IdName
from redi.client import client
from redi.i18n import messages
import sys


class TimeEntry(TypedDict):
    """redmine TimeEntry

    GET /time_entries.json / GET /time_entries/{id}.json を実行して確認できた
    フィールドを記載。`issue` はチケットに紐づく作業時間の場合のみ存在し、
    `id` のみを持つ（件名は含まれないため別途 fetch_issue_subjects で取得する）。
    """

    id: int
    project: IdName
    user: IdName
    activity: IdName
    hours: float
    comments: str | None
    spent_on: str  # YYYY-MM-DD
    created_on: str
    updated_on: str
    # チケットに紐づく作業時間の場合のみ存在
    issue: NotRequired[TimeEntryIssueRef]


class TimeEntryIssueRef(TypedDict):
    """作業時間が参照するチケット。`id` のみを持つ。"""

    id: int


class TimeEntriesPageResponse(TypedDict):
    """GET /time_entries.json のレスポンス"""

    time_entries: list[TimeEntry]
    total_count: int
    offset: int
    limit: int


def create_time_entry(
    issue_id: str | None = None,
    project_id: str | None = None,
    hours: float = 0,
    activity_id: str | None = None,
    spent_on: str | None = None,
    comments: str | None = None,
) -> None:
    """作業時間を作成する

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
    """
    if not issue_id and not project_id:
        print(messages.issue_or_project_id_required)
        sys.exit(1)
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
    if response.status_code == 422:
        raise RedmineValidationException.from_response("time_entry", "create", response)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.time_entry_create_failed)
        sys.exit(1)
    created = cast("TimeEntry", response.json()["time_entry"])
    print(
        messages.time_entry_created.format(
            id=created["id"], hours=created["hours"], spent_on=created["spent_on"]
        )
    )


COMMENT_PREVIEW_MAX_LEN = 30


def format_time_entry_line(
    te: TimeEntry,
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


def fetch_time_entries_page(
    project_id: str | None = None,
    user_id: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> TimeEntriesPageResponse:
    if project_id:
        path = f"/projects/{project_id}/time_entries.json"
    else:
        path = "/time_entries.json"
    params: dict = {}
    if user_id:
        params["user_id"] = user_id
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    response = client.get(path, params=params)
    response.raise_for_status()
    return cast("TimeEntriesPageResponse", response.json())


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
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    full: bool = False,
) -> None:
    if project_id:
        path = f"/projects/{project_id}/time_entries.json"
    else:
        path = "/time_entries.json"
    params: dict = {}
    if user_id:
        params["user_id"] = user_id
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    response = client.get(path, params=params)
    response.raise_for_status()
    time_entries = cast("list[TimeEntry]", response.json()["time_entries"])
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


def fetch_time_entry(time_entry_id: str) -> TimeEntry:
    response = client.get(f"/time_entries/{time_entry_id}.json")
    if response.status_code == 404:
        print(messages.time_entry_not_found.format(id=time_entry_id))
        sys.exit(1)
    response.raise_for_status()
    return cast("TimeEntry", response.json()["time_entry"])


def read_time_entry(time_entry_id: str, full: bool = False) -> None:
    te = fetch_time_entry(time_entry_id)
    if full:
        print(json.dumps(te, ensure_ascii=False))
        return
    lines = [
        f"{te['id']} {te['hours']}h {te['activity']['name']} ({te['spent_on']})",
        messages.label_project_in_te.format(
            name=te["project"]["name"], id=te["project"]["id"]
        ),
        messages.label_user_in_te.format(name=te["user"]["name"], id=te["user"]["id"]),
    ]
    issue = te.get("issue")
    if issue:
        lines.append(messages.label_issue_field.format(id=issue["id"]))
    comments = te.get("comments")
    if comments:
        lines.append(messages.label_comments_field.format(value=comments))
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
    """作業時間を更新する

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
    """
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
        sys.exit(1)
    response = client.put(
        f"/time_entries/{time_entry_id}.json", json={"time_entry": data}
    )
    if response.status_code == 422:
        raise RedmineValidationException.from_response("time_entry", "update", response)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.time_entry_update_failed)
        sys.exit(1)
    print(messages.time_entry_updated.format(id=time_entry_id))


def delete_time_entry(time_entry_id: str) -> None:
    response = client.delete(f"/time_entries/{time_entry_id}.json")
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.time_entry_delete_failed)
        sys.exit(1)
    print(messages.time_entry_deleted.format(id=time_entry_id))
