from __future__ import annotations

from typing import NotRequired, TypedDict, cast

from redi.api.exceptions import RedmineValidationException
from redi.api.types import IdName
from redi.client import client


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


class TimeEntryNotFoundException(Exception):
    def __init__(self, time_entry_id: str) -> None:
        super().__init__(time_entry_id)
        self.time_entry_id = time_entry_id


def create_time_entry(
    issue_id: str | None = None,
    project_id: str | None = None,
    hours: float = 0,
    activity_id: str | None = None,
    spent_on: str | None = None,
    comments: str | None = None,
) -> TimeEntry:
    """作業時間を作成し、作成された作業時間を返す

    Args:
        project_id: time_entries は他の API と異なり slug を受け付けないため数値の id を渡す
                    https://www.redmine.org/projects/redmine/wiki/Rest_TimeEntries

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 422 以外の HTTP エラーが返った場合
    """
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
    response.raise_for_status()
    return cast("TimeEntry", response.json()["time_entry"])


def fetch_time_entries_page(
    project_id: str | None = None,
    user_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
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


def fetch_time_entry(time_entry_id: str) -> TimeEntry | None:
    """作業時間を取得する。存在しない場合 (HTTP 404) は None を返す。"""
    response = client.get(f"/time_entries/{time_entry_id}.json")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return cast("TimeEntry", response.json()["time_entry"])


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

    Args:
        project_id: time_entries は他の API と異なり slug を受け付けないため数値の id を渡す
                    https://www.redmine.org/projects/redmine/wiki/Rest_TimeEntries

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 422 以外の HTTP エラーが返った場合
    """
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
    response = client.put(
        f"/time_entries/{time_entry_id}.json", json={"time_entry": data}
    )
    if response.status_code == 422:
        raise RedmineValidationException.from_response("time_entry", "update", response)
    response.raise_for_status()


def delete_time_entry(time_entry_id: str) -> None:
    """作業時間を削除する

    Raises:
        TimeEntryNotFoundException: 対象の作業時間が存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.delete(f"/time_entries/{time_entry_id}.json")
    if response.status_code == 404:
        raise TimeEntryNotFoundException(time_entry_id)
    response.raise_for_status()
