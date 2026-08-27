"""イシューの標準項目を対話で入力する。

create / update の対話フローで二重に書かれていた入力処理をまとめたもの。
値を返すだけで args への代入や後続の変換は呼び出し側に任せる。

対象バージョンや期日など issue の項目に固有の処理なのでこのパッケージに置く。
issue 非依存のカスタムフィールド入力は cli/custom_field_prompt.py にある。
"""

from datetime import date

from redi.api.membership import fetch_project_users
from redi.cli.interactive import prompt
from redi.cli.keybinding import (
    date_key_bindings,
    digit_and_period_key_bindings,
    digit_only_key_bindings,
)
from redi.cli.picker import inline_choice
from redi.cli.validator import (
    DateValidator,
    DueDateValidator,
    HourValidator,
    IntValidator,
)
from redi.i18n import messages
from redi.service import project_service, version_service


def prompt_project(default: str = "") -> str:
    """プロジェクトを選ばせて数値の id を返す。"""
    projects = project_service.list_projects()
    options: list[tuple[str, str]] = [(str(p["id"]), p["name"]) for p in projects]
    labels = dict(options)
    value = inline_choice(messages.prompt_select_project, options, default=default)
    print(messages.project_label.format(value=labels[value]))
    return value


def prompt_assignee(project_id: str, default: str = "") -> str:
    """担当者を選ばせて id を返す。「なし」を選んだ場合は空文字。"""
    users = fetch_project_users(project_id)
    options: list[tuple[str, str]] = [("", messages.prompt_select_assignee_none)] + [
        (str(u["id"]), u.get("name", "")) for u in users
    ]
    labels = dict(options)
    value = inline_choice(messages.prompt_select_assignee, options, default=default)
    print(messages.assignee_label.format(value=labels[value]))
    return value


def prompt_fixed_version(project_id: str, default: str = "") -> str:
    """対象バージョンを選ばせて id を返す。「なし」を選んだ場合は空文字。"""
    versions = version_service.list_versions(project_id)
    options: list[tuple[str, str]] = [
        ("", messages.prompt_select_fixed_version_none)
    ] + [(str(v["id"]), f"{v['name']} ({v['status']})") for v in versions]
    labels = dict(options)
    value = inline_choice(
        messages.prompt_select_fixed_version, options, default=default
    )
    print(messages.fixed_version_label.format(value=labels[value]))
    return value


def prompt_parent_issue_id(default: str = "") -> str:
    """親チケットの id を入力させる。空のまま確定した場合は空文字。"""
    return prompt(
        messages.prompt_parent_issue_id,
        default=default,
        validator=IntValidator(allow_empty=True),
        key_bindings=digit_only_key_bindings(),
    ).strip()


def prompt_start_date(default: str = "") -> str:
    """開始日を入力させる。空のまま確定した場合は空文字。"""
    return prompt(
        messages.prompt_start_date,
        default=default,
        validator=DateValidator(allow_empty=True),
        key_bindings=date_key_bindings(),
    ).strip()


def prompt_due_date(start_date: date | None, default: str = "") -> str:
    """期日を入力させる。空のまま確定した場合は空文字。

    start_date を渡すとそれより前の日付を弾く。
    """
    return prompt(
        messages.prompt_due_date,
        default=default,
        validator=DueDateValidator(start_date),
        key_bindings=date_key_bindings(),
    ).strip()


def prompt_estimated_hours(default: str = "") -> float | None:
    """予定工数を入力させる。空のまま確定した場合は None。"""
    value = prompt(
        messages.prompt_estimated_hours,
        default=default,
        validator=HourValidator(allow_empty=True),
        key_bindings=digit_and_period_key_bindings(),
    ).strip()
    return float(value) if value else None


def parse_iso_date(text: str | None) -> date | None:
    """ISO 形式の日付文字列を date にする。空や不正な値は None。"""
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None
