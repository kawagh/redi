"""イシュー操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.issue` が持つ。
"""

from __future__ import annotations

from redi import config
from redi.api import issue as issue_api
from redi.api.issue import Issue
from redi.service.attachment_service import upload_file


def issue_url(issue_id: str, note_number: int | None = None) -> str:
    """イシューの Web UI 上の URL を組み立てる。"""
    url = f"{config.redmine_url}/issues/{issue_id}"
    if note_number is not None:
        url = f"{url}#note-{note_number}"
    return url


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
) -> list[Issue]:
    """イシュー一覧を取得する。"""
    return issue_api.fetch_issues(
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


def read_issue(issue_id: str, include: str = "") -> Issue:
    """イシューを取得する。

    Raises:
        IssueNotFoundException: 対象イシューが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return issue_api.fetch_issue(issue_id, include=include)


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
    """イシューを作成し、作成されたイシューを返す。

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return issue_api.create_issue(
        project_id=project_id,
        subject=subject,
        description=description,
        tracker_id=tracker_id,
        priority_id=priority_id,
        assigned_to_id=assigned_to_id,
        fixed_version_id=fixed_version_id,
        parent_issue_id=parent_issue_id,
        start_date=start_date,
        due_date=due_date,
        estimated_hours=estimated_hours,
        custom_fields=custom_fields,
    )


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
    custom_fields: list[dict] | None = None,
    attachments: list[str] | None = None,
) -> None:
    """イシューを更新する。添付ファイルが指定されていれば先にアップロードする。

    Raises:
        LocalFileNotFoundException: `attachments` に存在しないパスが含まれる
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    uploads = [upload_file(file_path) for file_path in attachments or []]
    issue_api.update_issue(
        issue_id=issue_id,
        subject=subject,
        description=description,
        tracker_id=tracker_id,
        status_id=status_id,
        priority_id=priority_id,
        assigned_to_id=assigned_to_id,
        fixed_version_id=fixed_version_id,
        parent_issue_id=parent_issue_id,
        start_date=start_date,
        due_date=due_date,
        done_ratio=done_ratio,
        estimated_hours=estimated_hours,
        notes=notes,
        custom_fields=custom_fields,
        uploads=uploads,
    )


def delete_issue(issue_id: str) -> None:
    """イシューを削除する。

    Raises:
        IssueNotFoundException: 対象イシューが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    issue_api.delete_issue(issue_id)


def add_note(issue_id: str, notes: str) -> str:
    """イシューにコメントを追加し、追加したコメントの URL を返す。

    Redmine はコメント追加のレスポンスに note 番号を含めないため、
    追加後にジャーナル(プロパティ変更履歴やコメント)を数えて番号を決める。

    Raises:
        IssueNotFoundException: 対象イシューが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    issue_api.add_note(issue_id, notes)
    issue = issue_api.fetch_issue(issue_id, include="journals")
    journals = issue.get("journals") or []
    if not journals:
        return issue_url(issue_id)
    return issue_url(issue_id, note_number=len(journals))


def add_watcher(issue_id: str, user_id: int) -> None:
    """イシューにウォッチャーを追加する。

    Raises:
        IssueNotFoundException: 対象イシューが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    issue_api.add_watcher(issue_id, user_id)


def remove_watcher(issue_id: str, user_id: int) -> None:
    """イシューからウォッチャーを削除する。

    Raises:
        WatcherNotFoundException: イシューまたはユーザーが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    issue_api.remove_watcher(issue_id, user_id)
