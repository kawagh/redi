"""フィルタ modal の選択肢を組み立てる。"""

from redi.api.issue_status import fetch_issue_statuses
from redi.api.membership import fetch_project_users
from redi.api.tracker import fetch_trackers
from redi.i18n import messages


def build_status_choices() -> list[tuple[str | None, str]]:
    """フィルタモーダルのステータス選択肢。先頭の3つは Redmine の特殊指定。"""
    choices: list[tuple[str | None, str]] = [
        (None, messages.tui_filter_status_open_default),
        ("*", messages.tui_filter_status_all),
        ("closed", messages.tui_filter_status_closed_only),
    ]
    for s in fetch_issue_statuses():
        choices.append((str(s["id"]), s.get("name", "")))
    return choices


def build_tracker_choices() -> list[tuple[str | None, str]]:
    """フィルタモーダルのトラッカー選択肢。先頭は特殊指定 (未設定)。"""
    choices: list[tuple[str | None, str]] = [
        (None, messages.tui_filter_assignee_none),
    ]
    for t in fetch_trackers():
        choices.append((str(t["id"]), t.get("name", "")))
    return choices


def build_assignee_choices(
    project_id: str | None, me_id: str | None = None
) -> list[tuple[str | None, str]]:
    """フィルタモーダルの担当者選択肢。先頭は特殊指定 (未設定/me/未割当)。

    `me_id` が指定されていれば、`fetch_project_users` の結果から自身を除外して
    「自分」項目との重複表示を避ける。
    """
    choices: list[tuple[str | None, str]] = [
        (None, messages.tui_filter_assignee_none),
        ("me", messages.tui_filter_assignee_me),
        ("!*", messages.tui_filter_assignee_unassigned),
    ]
    if project_id:
        for u in fetch_project_users(project_id):
            uid = str(u["id"])
            if me_id is not None and uid == me_id:
                continue
            choices.append((uid, u.get("name", "")))
    return choices


def build_user_choices(
    project_id: str | None, me_id: str | None = None
) -> list[tuple[str | None, str]]:
    """time_entry フィルタモーダルのユーザー選択肢。先頭は特殊指定 (未設定/自分)。

    `me_id` が指定されていれば、`fetch_project_users` の結果から自身を除外して
    「自分」項目との重複表示を避ける。
    """
    choices: list[tuple[str | None, str]] = [
        (None, messages.tui_filter_assignee_none),
        ("me", messages.tui_filter_assignee_me),
    ]
    if project_id:
        for u in fetch_project_users(project_id):
            uid = str(u["id"])
            if me_id is not None and uid == me_id:
                continue
            choices.append((uid, u.get("name", "")))
    return choices
