"""作業時間操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.time_entry` が持つ。
"""

from redi.api import time_entry as time_entry_api
from redi.api.time_entry import TimeEntriesPageResponse, TimeEntry
from redi.service.project_service import resolve_project_id

COMMENT_PREVIEW_MAX_LEN = 30


def format_time_entry_line(
    te: TimeEntry,
    include_user: bool = True,
    issue_subjects: dict[int, str] | None = None,
) -> str:
    """作業時間 1 件を CLI の一覧 / TUI の行として表示する文字列に整える。"""
    # 列順: id / 日付 / 人 / 時間 / 活動 / チケット(またはプロジェクト名) / コメント
    # 活動は `view` に合わせて時間の直後に置く。
    parts = [str(te["id"]), f"({te['spent_on']})"]
    if include_user:
        user = te.get("user") or {}
        name = user.get("name")
        if name:
            parts.append(name)
    parts.append(f"{te['hours']}h")
    activity = te.get("activity") or {}
    activity_name = activity.get("name")
    if activity_name:
        parts.append(activity_name)
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


def fetch_page(
    project_id: str | None = None,
    user_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> TimeEntriesPageResponse:
    """条件に合う作業時間を総件数付きの 1 ページとして取得する。"""
    return time_entry_api.fetch_time_entries_page(
        project_id=project_id,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


def fetch_issue_subjects(entries: list[TimeEntry]) -> dict[int, str]:
    """作業時間が参照するチケットの件名を id -> 件名 で返す。

    作業時間のレスポンスは `issue` に id しか持たないため別途引く。
    """
    issue_ids = sorted(
        {
            te["issue"]["id"]
            for te in entries
            if te.get("issue") and te["issue"].get("id")
        }
    )
    return time_entry_api.fetch_issue_subjects(issue_ids)


def read_time_entry(time_entry_id: str) -> TimeEntry | None:
    """作業時間を取得する。存在しない場合は None を返す。"""
    return time_entry_api.fetch_time_entry(time_entry_id)


def create_time_entry(
    issue_id: str | None = None,
    project_id: str | None = None,
    hours: float = 0,
    activity_id: str | None = None,
    spent_on: str | None = None,
    comments: str | None = None,
) -> TimeEntry:
    """作業時間を作成する。project_id は数値の id に解決してから渡す。

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    if project_id is not None:
        project_id = resolve_project_id(project_id)
    return time_entry_api.create_time_entry(
        issue_id=issue_id,
        project_id=project_id,
        hours=hours,
        activity_id=activity_id,
        spent_on=spent_on,
        comments=comments,
    )


def update_time_entry(
    time_entry_id: str,
    hours: float | None = None,
    issue_id: str | None = None,
    project_id: str | None = None,
    activity_id: str | None = None,
    spent_on: str | None = None,
    comments: str | None = None,
) -> None:
    """作業時間を更新する。project_id は数値の id に解決してから渡す。

    Raises:
        TimeEntryNotFoundException: 対象の作業時間が存在しない (HTTP 404)
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    if project_id is not None:
        project_id = resolve_project_id(project_id)
    time_entry_api.update_time_entry(
        time_entry_id,
        hours=hours,
        issue_id=issue_id,
        project_id=project_id,
        activity_id=activity_id,
        spent_on=spent_on,
        comments=comments,
    )


def delete_time_entry(time_entry_id: str) -> None:
    """作業時間を削除する。

    Raises:
        TimeEntryNotFoundException: 対象の作業時間が存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    time_entry_api.delete_time_entry(time_entry_id)
