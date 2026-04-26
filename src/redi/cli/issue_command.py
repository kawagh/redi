import argparse
import re
from datetime import date

from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator

from redi.cli._common import (
    confirm_delete,
    inline_checkbox,
    inline_choice,
    open_editor,
    resolve_alias,
)
from redi.cli.prompt_util import DueDateValidator, HourValidator
from redi.config import default_project_id
from redi.api.enumeration import fetch_issue_priorities, fetch_time_entry_activities
from redi.api.issue import (
    add_note,
    add_watcher,
    create_issue,
    delete_issue,
    fetch_issue,
    fetch_issues,
    list_issues,
    read_issue,
    remove_watcher,
    update_issue,
)
from redi.api.issue_relation import create_relation, delete_relation
from redi.api.issue_status import fetch_issue_statuses
from redi.api.membership import fetch_project_users
from redi.api.time_entry import create_time_entry
from redi.api.tracker import fetch_trackers
from redi.api.version import fetch_versions
from redi.i18n import messages

from redi.api.custom_field import (
    fetch_custom_fields,
    fetch_project_issue_custom_field_ids,
    filter_required_issue_custom_fields,
)


def add_issue_parser(subparsers: argparse._SubParsersAction) -> None:
    i_parser = subparsers.add_parser(
        "issue",
        aliases=["i"],
        help=messages.arg_help_issue_command,
    )
    i_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    i_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_issue_filter_project
    )
    i_parser.add_argument(
        "--version",
        "-v",
        help=messages.arg_help_issue_filter_version,
    )
    i_parser.add_argument(
        "--assigned_to",
        "-a",
        help=messages.arg_help_issue_filter_assigned_to,
    )
    i_parser.add_argument(
        "--status_id",
        "-s",
        help=messages.arg_help_issue_filter_status,
    )
    i_parser.add_argument(
        "--tracker_id", "-t", help=messages.arg_help_issue_filter_tracker
    )
    i_parser.add_argument("--priority_id", help=messages.arg_help_issue_filter_priority)
    i_parser.add_argument(
        "--query_id",
        "-q",
        help=messages.arg_help_issue_filter_query,
    )
    i_parser.add_argument("--limit", "-l", type=int, help=messages.arg_help_limit)
    i_parser.add_argument("--offset", "-o", type=int, help=messages.arg_help_offset)
    i_subparsers = i_parser.add_subparsers(dest="issue_command")
    i_subparsers.add_parser("list", aliases=["l"], help=messages.arg_help_issue_list)
    i_view_parser = i_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_issue_view
    )
    i_view_parser.add_argument("issue_id", help=messages.arg_help_issue_view_id)
    i_view_parser.add_argument(
        "--include",
        help=messages.arg_help_issue_include,
    )
    i_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    i_view_parser.add_argument(
        "--web", "-w", action="store_true", help=messages.arg_help_open_web
    )
    i_create_parser = i_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_issue_create
    )
    i_create_parser.add_argument(
        "subject", nargs="?", help=messages.arg_help_issue_subject_arg
    )
    i_create_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_project_id
    )
    i_create_parser.add_argument(
        "--tracker_id", "-t", help=messages.arg_help_issue_tracker_id
    )
    i_create_parser.add_argument(
        "--priority_id", help=messages.arg_help_issue_priority_id
    )
    i_create_parser.add_argument(
        "--assigned_to_id", "-a", help=messages.arg_help_issue_assigned_to_id
    )
    i_create_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help=messages.arg_help_issue_description,
    )
    i_create_parser.add_argument(
        "--custom_fields",
        help=messages.arg_help_custom_fields,
    )
    i_update_parser = i_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_issue_update
    )
    i_update_parser.add_argument(
        "issue_id", nargs="?", help=messages.arg_help_issue_update_id
    )
    i_update_parser.add_argument(
        "--subject", "-s", help=messages.arg_help_issue_subject_opt
    )
    i_update_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help=messages.arg_help_issue_update_description,
    )
    i_update_parser.add_argument(
        "--tracker_id", "-t", help=messages.arg_help_issue_update_tracker_id
    )
    i_update_parser.add_argument("--status_id", help=messages.arg_help_issue_status_id)
    i_update_parser.add_argument(
        "--priority_id", help=messages.arg_help_issue_priority_id
    )
    i_update_parser.add_argument(
        "--assigned_to_id", "-a", help=messages.arg_help_issue_assigned_to_id
    )
    i_update_parser.add_argument(
        "--fixed_version_id", help=messages.arg_help_issue_fixed_version_id
    )
    i_update_parser.add_argument(
        "--parent_issue_id", help=messages.arg_help_issue_parent
    )
    i_update_parser.add_argument(
        "--start_date", help=messages.arg_help_issue_start_date
    )
    i_update_parser.add_argument("--due_date", help=messages.arg_help_issue_due_date)
    i_update_parser.add_argument(
        "--done_ratio", type=int, help=messages.arg_help_issue_done_ratio
    )
    i_update_parser.add_argument(
        "--estimated_hours", type=float, help=messages.arg_help_issue_estimated_hours
    )
    i_update_parser.add_argument("--notes", "-n", help=messages.arg_help_issue_notes)
    i_update_parser.add_argument(
        "--custom_fields",
        help=messages.arg_help_custom_fields,
    )
    i_update_parser.add_argument(
        "--relate",
        help=messages.arg_help_issue_relate,
    )
    i_update_parser.add_argument(
        "--to", dest="relate_to", help=messages.arg_help_issue_relate_to
    )
    i_update_parser.add_argument(
        "--delete-relation",
        action="store_true",
        help=messages.arg_help_issue_delete_relation,
    )
    i_update_parser.add_argument(
        "--attach",
        action="append",
        help=messages.arg_help_issue_attach,
    )
    i_update_parser.add_argument(
        "--hours", type=float, help=messages.arg_help_issue_hours
    )
    i_update_parser.add_argument(
        "--activity_id", help=messages.arg_help_issue_activity_id
    )
    i_update_parser.add_argument("--spent_on", help=messages.arg_help_issue_spent_on)
    i_update_parser.add_argument(
        "--time_comments", help=messages.arg_help_issue_time_comments
    )
    i_update_parser.add_argument(
        "--add-watcher",
        type=int,
        action="append",
        dest="add_watcher_ids",
        help=messages.arg_help_issue_add_watcher,
    )
    i_update_parser.add_argument(
        "--remove-watcher",
        type=int,
        action="append",
        dest="remove_watcher_ids",
        help=messages.arg_help_issue_remove_watcher,
    )
    i_comment_parser = i_subparsers.add_parser(
        "comment", aliases=["co"], help=messages.arg_help_issue_comment
    )
    i_comment_parser.add_argument("issue_id", help=messages.arg_help_issue_view_id)
    i_comment_parser.add_argument(
        "notes", nargs="?", default="", help=messages.arg_help_issue_comment_notes
    )
    i_delete_parser = i_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_issue_delete
    )
    i_delete_parser.add_argument("issue_id", help=messages.arg_help_issue_view_id)
    i_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def _interactive_select_issue_id() -> str:
    issues = fetch_issues(project_id=default_project_id)
    if not issues:
        print(messages.no_issues_available)
        exit(1)
    options: list[tuple[str, str]] = [
        (str(i["id"]), f"#{i['id']} {i['subject']}") for i in issues
    ]
    labels = dict(options)
    try:
        issue_id = inline_choice(messages.prompt_select_issue_to_update, options)
    except KeyboardInterrupt:
        print(messages.canceled)
        exit(1)
    print(messages.update_target_issue.format(label=labels[issue_id]))
    return issue_id


def _interactive_fill_issue_update_args(args: argparse.Namespace) -> None:
    current = fetch_issue(args.issue_id)
    field_values: list[tuple[str, str]] = [
        ("tracker", messages.field_tracker),
        ("subject", messages.field_subject),
        ("description", messages.field_description),
        ("status", messages.field_status),
        ("priority", messages.field_priority),
        ("assigned_to", messages.field_assignee),
        ("fixed_version", messages.field_fixed_version),
        ("start_date", messages.field_start_date),
        ("due_date", messages.field_due_date),
        ("done_ratio", messages.field_done_ratio),
        ("estimated_hours", messages.field_estimated_hours),
        ("notes", messages.field_notes),
        ("time_entry", messages.field_time_entry),
    ]
    try:
        selected = inline_checkbox(
            messages.prompt_select_update_items,
            field_values,
            initial_value="description",
        )
    except KeyboardInterrupt:
        print(messages.canceled)
        exit(1)
    if not selected:
        print(messages.canceled_no_items_selected)
        exit(1)
    labels = dict(field_values)
    print(messages.update_items.format(items=", ".join(labels[v] for v in selected)))
    try:
        if "tracker" in selected:
            trackers = fetch_trackers()
            tracker_options: list[tuple[str, str]] = [
                (str(t["id"]), t["name"]) for t in trackers
            ]
            tracker_labels = dict(tracker_options)
            args.tracker_id = inline_choice(
                messages.prompt_select_tracker, tracker_options
            )
            print(messages.tracker_label.format(value=tracker_labels[args.tracker_id]))
        if "subject" in selected:
            args.subject = prompt(
                messages.prompt_subject, default=current.get("subject") or ""
            ).strip()
        if "description" in selected:
            args.description = ""
        if "status" in selected:
            statuses = fetch_issue_statuses()
            status_options: list[tuple[str, str]] = [
                (str(s["id"]), s["name"]) for s in statuses
            ]
            status_labels = dict(status_options)
            args.status_id = inline_choice(
                messages.prompt_select_status, status_options
            )
            print(messages.status_label.format(value=status_labels[args.status_id]))
        if "priority" in selected:
            priorities = fetch_issue_priorities()
            priority_options: list[tuple[str, str]] = [
                (str(p["id"]), p["name"]) for p in priorities
            ]
            priority_labels = dict(priority_options)
            args.priority_id = inline_choice(
                messages.prompt_select_priority, priority_options
            )
            print(
                messages.priority_label.format(value=priority_labels[args.priority_id])
            )
        if "assigned_to" in selected:
            project_id = (current.get("project") or {}).get("id")
            if not project_id:
                print(messages.canceled_no_project)
                exit(1)
            users = fetch_project_users(str(project_id))
            assignee_options: list[tuple[str, str]] = [
                ("", messages.prompt_select_assignee_none)
            ] + [(str(u["id"]), u["name"]) for u in users]
            assignee_labels = dict(assignee_options)
            current_assignee_id = (current.get("assigned_to") or {}).get("id")
            default_assignee = (
                str(current_assignee_id) if current_assignee_id is not None else ""
            )
            args.assigned_to_id = inline_choice(
                messages.prompt_select_assignee,
                assignee_options,
                default=default_assignee,
            )
            print(
                messages.assignee_label.format(
                    value=assignee_labels[args.assigned_to_id]
                )
            )
        if "fixed_version" in selected:
            project_id = (current.get("project") or {}).get("id")
            if not project_id:
                print(messages.canceled_no_project)
                exit(1)
            versions = fetch_versions(str(project_id))
            version_options: list[tuple[str, str]] = [
                (str(v["id"]), f"{v['name']} ({v['status']})") for v in versions
            ]
            version_labels = dict(version_options)
            args.fixed_version_id = inline_choice(
                messages.prompt_select_fixed_version, version_options
            )
            print(
                messages.fixed_version_label.format(
                    value=version_labels[args.fixed_version_id]
                )
            )
        date_validator = Validator.from_callable(
            lambda v: v == "" or bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)),
            error_message=messages.error_date_format,
        )
        if "start_date" in selected:
            args.start_date = prompt(
                messages.prompt_start_date,
                default=current.get("start_date") or date.today().isoformat(),
                validator=date_validator,
            ).strip()
        if "due_date" in selected:
            effective_start = (
                args.start_date
                if "start_date" in selected
                else current.get("start_date")
            )
            start_date: date | None = None
            if effective_start:
                try:
                    start_date = date.fromisoformat(effective_start)
                except ValueError:
                    start_date = None
            args.due_date = prompt(
                messages.prompt_due_date,
                default=current.get("due_date") or date.today().isoformat(),
                validator=DueDateValidator(start_date),
            ).strip()
        if "done_ratio" in selected:
            ratio_options: list[tuple[str, str]] = [
                (str(r), f"{r}%") for r in range(0, 101, 10)
            ]
            current_ratio = current.get("done_ratio")
            default_ratio = str(current_ratio) if current_ratio is not None else None
            args.done_ratio = int(
                inline_choice(
                    messages.prompt_select_done_ratio,
                    ratio_options,
                    default=default_ratio,
                )
            )
            print(messages.done_ratio_label.format(value=args.done_ratio))
        if "estimated_hours" in selected:
            current_estimated = current.get("estimated_hours")
            default_estimated = (
                str(current_estimated) if current_estimated is not None else ""
            )
            args.estimated_hours = float(
                prompt(
                    messages.prompt_estimated_hours,
                    default=default_estimated,
                    validator=HourValidator(),
                ).strip()
            )
            print(messages.estimated_hours_label.format(value=args.estimated_hours))
        if "notes" in selected:
            args.notes = prompt(messages.prompt_comment).strip()
        if "time_entry" in selected:
            hours_str = prompt(messages.prompt_hours, validator=HourValidator()).strip()
            if hours_str:
                args.hours = float(hours_str)
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
            args.spent_on = prompt(messages.prompt_spent_on).strip() or None
            args.time_comments = prompt(messages.prompt_time_comments).strip() or None
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)


def _prompt_custom_field_value(cf: dict) -> str | None:
    name = cf.get("name", "")
    fmt = cf.get("field_format", "string")
    label = messages.prompt_required_field.format(name=name)
    # not support All formats
    if fmt == "list":
        possible = cf.get("possible_values") or []
        options: list[tuple[str, str]] = [
            (str(pv.get("value", "")), str(pv.get("value", "")))
            for pv in possible
            if pv.get("value", "") != ""
        ]
        if options:
            try:
                value = inline_choice(label, options)
            except KeyboardInterrupt:
                return None
            print(messages.prompt_field_value.format(name=name, value=value))
            return value
    try:
        return (
            prompt(messages.prompt_custom_field_label.format(name=label)).strip()
            or None
        )
    except (KeyboardInterrupt, EOFError):
        return None


def _interactive_fill_required_custom_fields(
    project_id: str, tracker_id: str | None, existing: str | None
) -> str | None:
    custom_fields = fetch_custom_fields()
    if custom_fields is None:
        # 非管理者はあらかじめ渡されているパラメータを使うしかない
        return existing
    project_cf_ids = fetch_project_issue_custom_field_ids(project_id)
    required = filter_required_issue_custom_fields(
        custom_fields, project_cf_ids, tracker_id
    )
    if not required:
        return existing

    existing_ids: set[int] = set()
    if existing:
        for pair in existing.split(","):
            key = pair.split("=")[0]
            existing_ids.add(int(key))

    added: list[str] = []
    for cf in required:
        if cf["id"] in existing_ids:
            continue
        value = _prompt_custom_field_value(cf)
        if value is None:
            print(messages.canceled)
            exit(1)
        added.append(f"{cf['id']}={value}")
    if not added:
        return existing
    if existing:
        return existing + "," + ",".join(added)
    return ",".join(added)


def handle_issue_create(args: argparse.Namespace) -> None:
    project_id = args.project_id or default_project_id
    if not project_id:
        print(messages.project_id_required)
        exit(1)
    subject = args.subject
    tracker_id = args.tracker_id
    custom_fields = args.custom_fields
    if subject is None:
        if tracker_id is None:
            trackers = fetch_trackers()
            tracker_options: list[tuple[str, str]] = [
                (str(t["id"]), t["name"]) for t in trackers
            ]
            labels = dict(tracker_options)
            try:
                tracker_id = inline_choice(
                    messages.prompt_select_tracker, tracker_options
                )
            except KeyboardInterrupt:
                print(messages.canceled)
                exit(1)
            print(messages.tracker_label.format(value=labels[tracker_id]))
        try:
            subject = prompt(messages.prompt_subject).strip()
        except (KeyboardInterrupt, EOFError):
            print(messages.canceled)
            exit(1)
        if not subject:
            print(messages.canceled_empty_subject)
            exit(1)
        # 必要なカスタムフィールドを対話的に入力
        custom_fields = _interactive_fill_required_custom_fields(
            project_id=project_id,
            tracker_id=tracker_id,
            existing=args.custom_fields,
        )
    if args.description is None:
        description = open_editor()
    else:
        description = args.description
    create_issue(
        project_id=project_id,
        subject=subject,
        description=description,
        tracker_id=tracker_id,
        priority_id=args.priority_id,
        assigned_to_id=args.assigned_to_id,
        custom_fields=custom_fields,
    )


def handle_issue_update(args: argparse.Namespace) -> None:
    if not args.issue_id:
        args.issue_id = _interactive_select_issue_id()
    no_args_provided = not (
        args.subject
        or args.description is not None
        or args.tracker_id
        or args.status_id
        or args.priority_id
        or args.assigned_to_id is not None
        or args.fixed_version_id
        or args.parent_issue_id is not None
        or args.start_date is not None
        or args.due_date is not None
        or args.done_ratio is not None
        or args.estimated_hours is not None
        or args.notes
        or args.custom_fields
        or args.relate
        or args.relate_to
        or args.delete_relation
        or args.attach
        or args.hours is not None
        or args.add_watcher_ids
        or args.remove_watcher_ids
    )
    if no_args_provided:
        _interactive_fill_issue_update_args(args)
    description = args.description
    if description is not None and description == "":
        current = fetch_issue(args.issue_id)
        description = open_editor(current.get("description") or "")
    should_update_issue = (
        args.subject
        or description is not None
        or args.tracker_id
        or args.status_id
        or args.priority_id
        or args.assigned_to_id is not None
        or args.fixed_version_id
        or args.parent_issue_id is not None
        or args.start_date is not None
        or args.due_date is not None
        or args.done_ratio is not None
        or args.estimated_hours is not None
        or args.notes
        or args.custom_fields
        or args.attach
    )
    should_update_issue_relation = args.delete_relation or (
        args.relate and args.relate_to
    )
    should_create_time_entry = args.hours is not None
    if should_update_issue:
        update_issue(
            issue_id=args.issue_id,
            subject=args.subject,
            description=description if description else None,
            tracker_id=args.tracker_id,
            status_id=args.status_id,
            priority_id=args.priority_id,
            assigned_to_id=args.assigned_to_id,
            fixed_version_id=args.fixed_version_id,
            parent_issue_id=args.parent_issue_id,
            start_date=args.start_date,
            due_date=args.due_date,
            done_ratio=args.done_ratio,
            estimated_hours=args.estimated_hours,
            notes=args.notes or "",
            custom_fields=args.custom_fields,
            attachments=args.attach,
        )
    if args.delete_relation:
        if not args.relate_to:
            print(messages.delete_relation_requires_to)
            exit(1)
        delete_relation(
            issue_id=args.issue_id,
            issue_to_id=args.relate_to,
        )
    elif args.relate and args.relate_to:
        create_relation(
            issue_id=args.issue_id,
            issue_to_id=args.relate_to,
            relation_type=args.relate,
        )
    elif args.relate or args.relate_to:
        print(messages.relate_and_to_required)
        exit(1)
    if should_create_time_entry:
        create_time_entry(
            issue_id=args.issue_id,
            hours=args.hours,
            activity_id=args.activity_id,
            spent_on=args.spent_on,
            comments=args.time_comments,
        )
    for user_id in args.add_watcher_ids or []:
        add_watcher(args.issue_id, user_id)
    for user_id in args.remove_watcher_ids or []:
        remove_watcher(args.issue_id, user_id)
    should_update_watchers = bool(args.add_watcher_ids or args.remove_watcher_ids)
    if (
        not should_update_issue
        and not should_update_issue_relation
        and not should_create_time_entry
        and not should_update_watchers
    ):
        print(messages.update_canceled_no_changes)
        exit(1)


def handle_issue(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.issue_command)
    if cmd == "view":
        read_issue(
            args.issue_id,
            include=args.include or "",
            full=args.full,
            web=args.web,
        )
    elif cmd == "create":
        handle_issue_create(args)
    elif cmd == "update":
        handle_issue_update(args)
    elif cmd == "comment":
        if args.notes:
            add_note(args.issue_id, args.notes)
        else:
            notes = open_editor()
            if notes:
                add_note(args.issue_id, notes)
            else:
                print(messages.canceled_empty_comment)
    elif cmd == "delete":
        if not args.yes:
            issue = fetch_issue(args.issue_id)
            confirm_delete(
                messages.delete_target_issue.format(
                    id=issue["id"], subject=issue["subject"]
                )
            )
        delete_issue(args.issue_id)
    elif cmd == "list" or cmd is None:
        list_issues(
            project_id=args.project_id or default_project_id,
            fixed_version_id=args.version,
            assigned_to=args.assigned_to,
            status_id=args.status_id,
            tracker_id=args.tracker_id,
            priority_id=args.priority_id,
            query_id=args.query_id,
            limit=args.limit,
            offset=args.offset,
            full=args.full,
        )
