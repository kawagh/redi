import argparse
import json
import sys

import requests
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator

from redi import config
from redi.api.enumeration import fetch_time_entry_activities
from redi.api.exceptions import ProjectNotFoundException, print_http_error_body
from redi.api.issue import Issue, IssueNotFoundException
from redi.api.time_entry import TimeEntry, TimeEntryNotFoundException
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.interactive import prompt
from redi.cli.keybinding import (
    date_key_bindings,
    digit_and_period_key_bindings,
    digit_only_key_bindings,
)
from redi.cli.picker import inline_checkbox, inline_choice
from redi.cli.shared_options import SharedOptionParser
from redi.cli.validator import DateValidator, HourValidator
from redi.i18n import messages
from redi.service import issue_service, project_service, time_entry_service


def _read_issue(issue_id: str) -> Issue:
    """作業時間の対象イシューを取得する。存在しない場合は exit 1。"""
    try:
        return issue_service.read_issue(issue_id)
    except IssueNotFoundException:
        print(messages.issue_not_found.format(id=issue_id))
        sys.exit(1)


def _fetch_time_entry_or_exit(time_entry_id: str) -> TimeEntry:
    """作業時間を取得する。存在しなければ見つからないと伝えて exit 1。"""
    te = time_entry_service.read_time_entry(time_entry_id)
    if te is None:
        print(messages.time_entry_not_found.format(id=time_entry_id))
        sys.exit(1)
    return te


def _list_time_entries(
    project_id: str | None = None,
    user_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    full: bool = False,
) -> None:
    """作業時間の一覧を標準出力に出す。full=True では取得した JSON をそのまま出す。"""
    entries = time_entry_service.fetch_page(
        project_id=project_id,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )["time_entries"]
    if full:
        print(json.dumps(entries, ensure_ascii=False))
        return
    issue_subjects = time_entry_service.fetch_issue_subjects(entries)
    # ユーザで絞り込んでいる場合は全行に同じ名前が並ぶので出さない
    for te in entries:
        print(
            time_entry_service.format_time_entry_line(
                te,
                include_user=user_id is None,
                issue_subjects=issue_subjects,
            )
        )


def _view_time_entry(time_entry_id: str, full: bool = False) -> None:
    """作業時間の詳細を標準出力に出す。存在しない場合は exit 1。"""
    te = _fetch_time_entry_or_exit(time_entry_id)
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


def create_time_entry(
    issue_id: str | None = None,
    project_id: str | None = None,
    hours: float = 0,
    activity_id: str | None = None,
    spent_on: str | None = None,
    comments: str | None = None,
) -> None:
    """作業時間を作成し、結果を標準出力に出す。失敗時は exit 1。

    `redi issue update --hours` からも使う。
    """
    if not issue_id and not project_id:
        print(messages.issue_or_project_id_required)
        sys.exit(1)
    try:
        created = time_entry_service.create_time_entry(
            issue_id=issue_id,
            project_id=project_id,
            hours=hours,
            activity_id=activity_id,
            spent_on=spent_on,
            comments=comments,
        )
    except ProjectNotFoundException as e:
        print(messages.project_not_found.format(id=e.project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.time_entry_create_failed)
        sys.exit(1)
    print(
        messages.time_entry_created.format(
            id=created["id"], hours=created["hours"], spent_on=created["spent_on"]
        )
    )


def _update_time_entry(
    time_entry_id: str,
    hours: float | None = None,
    issue_id: str | None = None,
    project_id: str | None = None,
    activity_id: str | None = None,
    spent_on: str | None = None,
    comments: str | None = None,
) -> None:
    """作業時間を更新し、結果を標準出力に出す。変更が無い場合と失敗時は exit 1。"""
    has_changes = (
        hours is not None
        or bool(issue_id)
        or bool(project_id)
        or bool(activity_id)
        or bool(spent_on)
        # 空文字はコメントを消す更新として送るため None かどうかで見る
        or comments is not None
    )
    if not has_changes:
        print(messages.update_canceled_no_changes)
        sys.exit(1)
    try:
        time_entry_service.update_time_entry(
            time_entry_id,
            hours=hours,
            issue_id=issue_id,
            project_id=project_id,
            activity_id=activity_id,
            spent_on=spent_on,
            comments=comments,
        )
    except TimeEntryNotFoundException:
        print(messages.time_entry_not_found.format(id=time_entry_id))
        sys.exit(1)
    except ProjectNotFoundException as e:
        print(messages.project_not_found.format(id=e.project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.time_entry_update_failed)
        sys.exit(1)
    print(messages.time_entry_updated.format(id=time_entry_id))


def _delete_time_entry(time_entry_id: str) -> None:
    """作業時間を削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        time_entry_service.delete_time_entry(time_entry_id)
    except TimeEntryNotFoundException:
        print(messages.time_entry_not_found.format(id=time_entry_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.time_entry_delete_failed)
        sys.exit(1)
    print(messages.time_entry_deleted.format(id=time_entry_id))


def _time_entry_list_option_parser(*, postfix: bool = False) -> argparse.ArgumentParser:
    """time_entry の一覧フィルタと出力形式のオプション"""
    parser = SharedOptionParser(postfix=postfix)
    parser.add_argument("--project_id", "-p", help=messages.arg_help_project_id)
    parser.add_argument("--user_id", "-u", help=messages.arg_help_time_entry_user_id)
    parser.add_argument(
        "--from",
        dest="from_date",
        help=messages.arg_help_time_entry_from,
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        help=messages.arg_help_time_entry_to,
    )
    parser.add_argument("--limit", "-l", type=int, help=messages.arg_help_limit)
    parser.add_argument("--offset", "-o", type=int, help=messages.arg_help_offset)
    parser.add_argument("--full", action="store_true", help=messages.arg_help_full_json)
    return parser


def add_time_entry_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    time_entry_parser = subparsers.add_parser(
        "time_entry",
        aliases=["te"],
        help=messages.arg_help_time_entry_command,
        parents=[*parents, _time_entry_list_option_parser()],
    )
    te_subparsers = time_entry_parser.add_subparsers(dest="time_entry_command")
    te_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_time_entry_list,
        parents=[*parents, _time_entry_list_option_parser(postfix=True)],
    )
    te_create_parser = te_subparsers.add_parser(
        "create",
        aliases=["c"],
        help=messages.arg_help_time_entry_create,
        parents=parents,
    )
    te_create_parser.add_argument(
        "hours", type=float, nargs="?", help=messages.arg_help_time_entry_hours
    )
    te_create_parser.add_argument(
        "--issue_id", "-i", help=messages.arg_help_time_entry_issue_id
    )
    te_create_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_project_id
    )
    te_create_parser.add_argument(
        "--activity_id", "-a", help=messages.arg_help_time_entry_activity_id
    )
    te_create_parser.add_argument(
        "--spent_on", help=messages.arg_help_time_entry_spent_on
    )
    te_create_parser.add_argument(
        "--comments", "-c", help=messages.arg_help_time_entry_comments
    )
    te_view_parser = te_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_time_entry_view, parents=parents
    )
    te_view_parser.add_argument(
        "time_entry_id", help=messages.arg_help_time_entry_view_id
    )
    te_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    te_update_parser = te_subparsers.add_parser(
        "update",
        aliases=["u"],
        help=messages.arg_help_time_entry_update,
        parents=parents,
    )
    te_update_parser.add_argument(
        "time_entry_id", help=messages.arg_help_time_entry_update_id
    )
    te_update_parser.add_argument(
        "--hours", type=float, help=messages.arg_help_time_entry_update_hours
    )
    te_update_parser.add_argument(
        "--issue_id", "-i", help=messages.arg_help_time_entry_issue_id
    )
    te_update_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_project_id
    )
    te_update_parser.add_argument(
        "--activity_id", "-a", help=messages.arg_help_time_entry_activity_id
    )
    te_update_parser.add_argument(
        "--spent_on", help=messages.arg_help_time_entry_update_spent_on
    )
    te_update_parser.add_argument(
        "--comments", "-c", help=messages.arg_help_time_entry_comments
    )
    te_delete_parser = te_subparsers.add_parser(
        "delete",
        aliases=["d"],
        help=messages.arg_help_time_entry_delete,
        parents=parents,
    )
    te_delete_parser.add_argument(
        "time_entry_id", help=messages.arg_help_time_entry_delete_id
    )
    te_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def _interactive_fill_time_entry_create_args(args: argparse.Namespace) -> None:
    try:
        if not args.issue_id and not args.project_id:
            default_issue_id = getattr(args, "default_issue_id", None) or ""
            issue_id = prompt(
                messages.prompt_issue_id_or_project,
                default=default_issue_id,
                key_bindings=digit_only_key_bindings(),
            ).strip()
            if issue_id:
                args.issue_id = issue_id
                issue = _read_issue(issue_id)
                print(
                    messages.issue_label.format(
                        id=issue["id"], subject=issue["subject"]
                    )
                )
            else:
                projects = project_service.list_projects()
                valid_values: set[str] = set()
                for p in projects:
                    valid_values.add(str(p["id"]))
                    if p.get("identifier"):
                        valid_values.add(p["identifier"])
                    if p.get("name"):
                        valid_values.add(p["name"])
                project_validator = Validator.from_callable(
                    lambda v: v in valid_values,
                    error_message=messages.error_no_matching_project,
                )
                completer = WordCompleter(
                    sorted(valid_values), ignore_case=True, match_middle=True
                )
                project_id = prompt(
                    messages.prompt_project_id_or_name,
                    default=config.default_project_id or "",
                    validator=project_validator,
                    completer=completer,
                ).strip()
                args.project_id = project_id
        hours_str = prompt(
            messages.prompt_hours,
            validator=HourValidator(),
            key_bindings=digit_and_period_key_bindings(),
        ).strip()
        args.hours = float(hours_str)
        if not args.activity_id:
            activities = fetch_time_entry_activities()
            activity_options: list[tuple[str, str]] = [
                (str(a["id"]), a["name"]) for a in activities
            ]
            activity_labels = dict(activity_options)
            args.activity_id = inline_choice(
                messages.prompt_select_activity, activity_options
            )
            print(
                messages.activity_label.format(value=activity_labels[args.activity_id])
            )
        if not args.spent_on:
            args.spent_on = (
                prompt(
                    messages.prompt_spent_on,
                    validator=DateValidator(allow_empty=True),
                    key_bindings=date_key_bindings(),
                ).strip()
                or None
            )
        if not args.comments:
            args.comments = prompt(messages.prompt_comment).strip() or None
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)


def _interactive_fill_time_entry_update_args(args: argparse.Namespace) -> None:
    current = _fetch_time_entry_or_exit(args.time_entry_id)
    field_values: list[tuple[str, str]] = [
        ("hours", messages.field_hours),
        ("activity", messages.field_activity),
        ("spent_on", messages.field_spent_on),
        ("comments", messages.field_comments),
        ("issue_id", messages.field_issue_id),
    ]
    try:
        selected = inline_checkbox(messages.prompt_select_update_items, field_values)
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)
    if not selected:
        print(messages.canceled_no_items_selected)
        sys.exit(1)
    labels = dict(field_values)
    print(messages.update_items.format(items=", ".join(labels[v] for v in selected)))
    try:
        if "hours" in selected:
            hours_str = prompt(
                messages.prompt_hours,
                default=str(current.get("hours", "")),
                validator=HourValidator(),
                key_bindings=digit_and_period_key_bindings(),
            ).strip()
            args.hours = float(hours_str)
        if "activity" in selected:
            activities = fetch_time_entry_activities()
            activity_options: list[tuple[str, str]] = [
                (str(a["id"]), a["name"]) for a in activities
            ]
            activity_labels = dict(activity_options)
            current_activity_id = str((current.get("activity") or {}).get("id", ""))
            args.activity_id = inline_choice(
                messages.prompt_select_activity,
                activity_options,
                default=current_activity_id or None,
            )
            print(
                messages.activity_label.format(value=activity_labels[args.activity_id])
            )
        if "spent_on" in selected:
            args.spent_on = (
                prompt(
                    messages.prompt_update_spent_on,
                    default=current.get("spent_on", "") or "",
                    validator=DateValidator(allow_empty=True),
                    key_bindings=date_key_bindings(),
                ).strip()
                or None
            )
        if "comments" in selected:
            args.comments = prompt(
                messages.prompt_comment, default=current.get("comments", "") or ""
            )
        if "issue_id" in selected:
            current_issue_id = str((current.get("issue") or {}).get("id", ""))
            issue_id = prompt(
                messages.prompt_issue_id_update,
                default=current_issue_id,
                key_bindings=digit_only_key_bindings(),
            ).strip()
            if issue_id:
                issue = _read_issue(issue_id)
                print(
                    messages.issue_label.format(
                        id=issue["id"], subject=issue["subject"]
                    )
                )
                args.issue_id = issue_id
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)


def handle_time_entry(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.time_entry_command)
    if cmd == "create":
        if args.hours is None:
            _interactive_fill_time_entry_create_args(args)
        project_id = args.project_id or config.default_project_id
        create_time_entry(
            issue_id=args.issue_id,
            project_id=project_id,
            hours=args.hours,
            activity_id=args.activity_id,
            spent_on=args.spent_on,
            comments=args.comments,
        )
    elif cmd == "view":
        _view_time_entry(args.time_entry_id, full=args.full)
    elif cmd == "update":
        if (
            args.hours is None
            and args.issue_id is None
            and args.project_id is None
            and args.activity_id is None
            and args.spent_on is None
            and args.comments is None
        ):
            _interactive_fill_time_entry_update_args(args)
        _update_time_entry(
            time_entry_id=args.time_entry_id,
            hours=args.hours,
            issue_id=args.issue_id,
            project_id=args.project_id,
            activity_id=args.activity_id,
            spent_on=args.spent_on,
            comments=args.comments,
        )
    elif cmd == "delete":
        if not args.yes:
            te = _fetch_time_entry_or_exit(args.time_entry_id)
            activity = (te.get("activity") or {}).get("name", "")
            confirm_delete(
                messages.delete_target_time_entry.format(
                    id=te["id"],
                    hours=te["hours"],
                    activity=activity,
                    spent_on=te["spent_on"],
                )
            )
        _delete_time_entry(args.time_entry_id)
    elif cmd == "list" or cmd is None:
        project_id = args.project_id or config.default_project_id
        _list_time_entries(
            project_id=project_id,
            user_id=args.user_id,
            from_date=args.from_date,
            to_date=args.to_date,
            limit=args.limit,
            offset=args.offset,
            full=args.full,
        )
