# Issue / IssueStatus / IssueCustomField / Journal / JournalDetail が
# 自分より下で定義される TypedDict を参照しているため、注釈の評価を遅らせる
from __future__ import annotations

from typing import NotRequired, TypedDict, cast

from redi.api.exceptions import ProjectNotFoundException, RedmineValidationException
from redi.api.types import IdName
from redi.client import client


class IssuesPageResponse(TypedDict):
    """GET /issues.json のレスポンス"""

    issues: list[Issue]
    total_count: int
    offset: int
    limit: int


class Issue(TypedDict):
    """redmine Issue"""

    id: int
    project: IdName
    tracker: IdName
    status: IssueStatus
    priority: IdName
    author: IdName
    # 担当者未割り当て時に存在しない
    assigned_to: NotRequired[IdName]
    subject: str
    description: str
    start_date: str | None
    due_date: str | None
    done_ratio: int
    is_private: bool
    estimated_hours: float | None
    total_estimated_hours: float | None
    spent_hours: float
    total_spent_hours: float
    # GET /issues/{id}では含まれる
    custom_fields: NotRequired[list[IssueCustomField]]
    created_on: str
    updated_on: str
    closed_on: str | None
    journals: NotRequired[list[Journal]]


class IssueCustomField(TypedDict):
    id: int
    name: str
    # valueがlist[str] の時に True
    multiple: NotRequired[bool]
    value: str | list[str]


class IssueStatus(TypedDict):
    id: int
    name: str
    is_closed: bool


class Journal(TypedDict):
    id: int
    user: IdName
    notes: str
    created_on: str
    updated_on: str
    private_notes: bool
    details: list[JournalDetail]


class JournalDetail(TypedDict):
    property: str  # ex. attr
    name: str  # ex. assigned_to_id
    old_value: str | None
    new_value: str | None


class IssueNotFoundException(Exception):
    def __init__(self, issue_id: str) -> None:
        super().__init__(issue_id)
        self.issue_id = issue_id


class WatcherNotFoundException(Exception):
    """ウォッチャー削除で 404 が返ったときに送出する例外。

    Redmine はイシューとユーザーのどちらが存在しないかを区別しないため両方を持つ。
    """

    def __init__(self, issue_id: str, user_id: int) -> None:
        super().__init__(f"{issue_id}/{user_id}")
        self.issue_id = issue_id
        self.user_id = user_id


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
) -> IssuesPageResponse:
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
    # 存在しない (または閲覧できない) プロジェクトを指定すると Redmine は 404 を返す
    if response.status_code == 404 and project_id:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()
    return cast(IssuesPageResponse, response.json())


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
) -> list[Issue]:
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


def fetch_issue(issue_id: str, include: str = "") -> Issue:
    """イシューを取得する

    Raises:
        IssueNotFoundException: 対象イシューが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    params = {}
    if include:
        params["include"] = include
    response = client.get(f"/issues/{issue_id}.json", params=params)
    if response.status_code == 404:
        raise IssueNotFoundException(issue_id)
    response.raise_for_status()
    return cast("Issue", response.json()["issue"])


def create_issue(
    project_id: str,
    subject: str,
    description: str = "",
    tracker_id: str | None = None,
    priority_id: str | None = None,
    assigned_to_id: str | None = None,
    fixed_version_id: str | None = None,
    parent_issue_id: str | None = None,
    start_date: str | None = None,
    due_date: str | None = None,
    estimated_hours: float | None = None,
    custom_fields: list[dict] | None = None,
) -> Issue:
    """イシューを作成し、作成されたイシューを返す

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 422 以外の HTTP エラーが返った場合
    """
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
    if fixed_version_id:
        issue_data["fixed_version_id"] = fixed_version_id
    if parent_issue_id:
        issue_data["parent_issue_id"] = parent_issue_id
    if start_date:
        issue_data["start_date"] = start_date
    if due_date:
        issue_data["due_date"] = due_date
    if estimated_hours is not None:
        issue_data["estimated_hours"] = estimated_hours
    if custom_fields:
        issue_data["custom_fields"] = custom_fields
    response = client.post("/issues.json", json={"issue": issue_data})
    if response.status_code == 422:
        raise RedmineValidationException.from_response("issue", "create", response)
    response.raise_for_status()
    return cast("Issue", response.json()["issue"])


def update_issue(
    issue_id: str,
    project_id: str | None = None,
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
    custom_fields: list[dict] | None = None,
    uploads: list[dict] | None = None,
) -> None:
    """イシューを更新する

    Args:
        project_id: 指定するとイシューを別プロジェクトへ移動する
        uploads: 添付ファイルのアップロード結果 (`api.attachment.upload_file` の戻り値)

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 422 以外の HTTP エラーが返った場合
    """
    issue_data: dict = {}
    if project_id:
        issue_data["project_id"] = project_id
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
    # 空文字は「対象バージョンを外す」意味なので assigned_to_id と同じく送る
    if fixed_version_id is not None:
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
        issue_data["custom_fields"] = custom_fields
    if uploads:
        issue_data["uploads"] = uploads
    response = client.put(f"/issues/{issue_id}.json", json={"issue": issue_data})
    if response.status_code == 422:
        raise RedmineValidationException.from_response("issue", "update", response)
    response.raise_for_status()


def add_watcher(issue_id: str, user_id: int) -> None:
    """イシューにウォッチャーを追加する

    Raises:
        IssueNotFoundException: 対象イシューが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.post(
        f"/issues/{issue_id}/watchers.json",
        json={"user_id": user_id},
    )
    if response.status_code == 404:
        raise IssueNotFoundException(issue_id)
    response.raise_for_status()


def remove_watcher(issue_id: str, user_id: int) -> None:
    """イシューからウォッチャーを削除する

    Raises:
        WatcherNotFoundException: イシューまたはユーザーが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.delete(f"/issues/{issue_id}/watchers/{user_id}.json")
    if response.status_code == 404:
        raise WatcherNotFoundException(issue_id, user_id)
    response.raise_for_status()


def delete_issue(issue_id: str) -> None:
    """イシューを削除する

    Raises:
        IssueNotFoundException: 対象イシューが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.delete(f"/issues/{issue_id}.json")
    if response.status_code == 404:
        raise IssueNotFoundException(issue_id)
    response.raise_for_status()


def add_note(issue_id: str, notes: str) -> None:
    """イシューにコメントを追加する

    Raises:
        IssueNotFoundException: 対象イシューが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.put(f"/issues/{issue_id}.json", json={"issue": {"notes": notes}})
    if response.status_code == 404:
        raise IssueNotFoundException(issue_id)
    response.raise_for_status()
