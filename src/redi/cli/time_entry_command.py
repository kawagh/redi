import argparse

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator

from redi.cli._common import (
    confirm_delete,
    inline_checkbox,
    inline_choice,
    resolve_alias,
)
from redi.cli.prompt_util import (
    HourValidator,
    digit_and_period_key_bindings,
    digit_only_key_bindings,
)
from redi.config import default_project_id
from redi.i18n import messages
from redi.api.enumeration import fetch_time_entry_activities
from redi.api.issue import fetch_issue
from redi.api.project import fetch_projects
from redi.api.time_entry import (
    create_time_entry,
    delete_time_entry,
    fetch_time_entry,
    list_time_entries,
    read_time_entry,
    update_time_entry,
)


def add_time_entry_parser(subparsers: argparse._SubParsersAction) -> None:
    time_entry_parser = subparsers.add_parser(
        "time_entry",
        help=messages.arg_help_time_entry_command,
    )
    time_entry_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_project_id
    )
    time_entry_parser.add_argument(
        "--user_id", "-u", help=messages.arg_help_time_entry_user_id
    )
    time_entry_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    te_subparsers = time_entry_parser.add_subparsers(dest="time_entry_command")
    te_subparsers.add_parser(
        "list", aliases=["l"], help=messages.arg_help_time_entry_list
    )
    te_create_parser = te_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_time_entry_create
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
        "view", aliases=["v"], help=messages.arg_help_time_entry_view
    )
    te_view_parser.add_argument(
        "time_entry_id", help=messages.arg_help_time_entry_view_id
    )
    te_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    te_update_parser = te_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_time_entry_update
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
        "delete", aliases=["d"], help=messages.arg_help_time_entry_delete
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
            issue_id = prompt(
                messages.prompt_issue_id_or_project,
                key_bindings=digit_only_key_bindings(),
            ).strip()
            if issue_id:
                args.issue_id = issue_id
                issue = fetch_issue(issue_id)
                print(
                    messages.issue_label.format(
                        id=issue["id"], subject=issue["subject"]
                    )
                )
            else:
                projects = fetch_projects()
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
                    default=default_project_id or "",
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
            args.spent_on = prompt(messages.prompt_spent_on).strip() or None
        if not args.comments:
            args.comments = prompt(messages.prompt_comment).strip() or None
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)


def _interactive_fill_time_entry_update_args(args: argparse.Namespace) -> None:
    current = fetch_time_entry(args.time_entry_id)
    field_values: list[tuple[str, str]] = [
        ("hours", messages.field_hours),
        ("activity", messages.field_activity),
        ("spent_on", messages.field_spent_on),
        ("comments", messages.field_comments),
        ("issue_id", messages.field_issue_id),
    ]
    try:
        selected = inline_checkbox(messages.prompt_select_update_items, field_values)
    except KeyboardInterrupt:
        print(messages.canceled)
        exit(1)
    if not selected:
        print(messages.canceled_no_items_selected)
        exit(1)
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
                issue = fetch_issue(issue_id)
                print(
                    messages.issue_label.format(
                        id=issue["id"], subject=issue["subject"]
                    )
                )
                args.issue_id = issue_id
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)


def handle_time_entry(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.time_entry_command)
    if cmd == "create":
        if args.hours is None:
            _interactive_fill_time_entry_create_args(args)
        project_id = args.project_id or default_project_id
        create_time_entry(
            issue_id=args.issue_id,
            project_id=project_id,
            hours=args.hours,
            activity_id=args.activity_id,
            spent_on=args.spent_on,
            comments=args.comments,
        )
    elif cmd == "view":
        read_time_entry(args.time_entry_id, full=args.full)
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
        update_time_entry(
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
            te = fetch_time_entry(args.time_entry_id)
            activity = (te.get("activity") or {}).get("name", "")
            confirm_delete(
                messages.delete_target_time_entry.format(
                    id=te["id"],
                    hours=te["hours"],
                    activity=activity,
                    spent_on=te["spent_on"],
                )
            )
        delete_time_entry(args.time_entry_id)
    elif cmd == "list" or cmd is None:
        project_id = args.project_id or default_project_id
        list_time_entries(project_id=project_id, user_id=args.user_id, full=args.full)
