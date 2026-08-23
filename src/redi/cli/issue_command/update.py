import argparse
import sys
from dataclasses import dataclass, fields
from datetime import date
from typing import Self, cast

import requests

from redi import config
from redi.api.custom_field import (
    CustomField,
    fetch_custom_fields,
    fetch_project_issue_custom_field_ids,
    filter_optional_issue_custom_fields,
    filter_required_issue_custom_fields,
)
from redi.api.enumeration import fetch_issue_priorities, fetch_time_entry_activities
from redi.api.exceptions import (
    ProjectNotFoundException,
    ProjectPermissionDeniedException,
    print_http_error_body,
)
from redi.api.issue import (
    Issue,
    IssueNotFoundException,
    WatcherNotFoundException,
)
from redi.api.issue_relation import RelationNotFoundException
from redi.api.issue_status import fetch_issue_statuses
from redi.cli.custom_field_prompt import (
    SKIP_UNSUPPORTED_FIELD,
    prompt_custom_field_value,
)
from redi.cli.editor import open_editor, save_body_on_failure
from redi.cli.interactive import prompt
from redi.cli.issue_command.custom_fields import parse_custom_fields
from redi.cli.issue_command.field_prompt import (
    parse_iso_date,
    prompt_assignee,
    prompt_due_date,
    prompt_estimated_hours,
    prompt_fixed_version,
    prompt_project,
    prompt_start_date,
)
from redi.cli.keybinding import date_key_bindings
from redi.cli.picker import inline_checkbox, inline_choice
from redi.cli.time_entry_command import create_time_entry
from redi.cli.validator import DateValidator, HourValidator
from redi.i18n import messages
from redi.service import issue_relation_service, issue_service, project_service
from redi.service.attachment_service import LocalFileNotFoundException
from redi.service.issue_relation_service import (
    RelatedIssueNotFoundException,
    RelationBetweenNotFoundException,
)


@dataclass
class IssueUpdateArgs:
    """`issue update` の入力値。

    フィールド名は `add_issue_parser` が定義する `dest` と一致させること。
    argparse 経由なら `from_namespace` で、TUI からは必要な項目だけ指定して生成する。
    """

    issue_id: str | None = None
    project_id: str | None = None
    subject: str | None = None
    description: str | None = None
    tracker_id: str | None = None
    status_id: str | None = None
    priority_id: str | None = None
    assigned_to_id: str | None = None
    fixed_version_id: str | None = None
    parent_issue_id: str | None = None
    start_date: str | None = None
    due_date: str | None = None
    done_ratio: int | None = None
    estimated_hours: float | None = None
    notes: str | None = None
    custom_fields: str | None = None
    relate: str | None = None
    relate_to: str | None = None
    delete_relation: bool = False
    attach: list[str] | None = None
    hours: float | None = None
    activity_id: str | None = None
    spent_on: str | None = None
    time_comments: str | None = None
    add_watcher_ids: list[int] | None = None
    remove_watcher_ids: list[int] | None = None

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> Self:
        # dest 名がずれていたら AttributeError で気付けるよう getattr は防御しない
        return cls(**{f.name: getattr(args, f.name) for f in fields(cls)})


def _read_issue(issue_id: str) -> Issue:
    """更新対象のイシューを取得する。存在しない場合は exit 1。"""
    try:
        return issue_service.read_issue(issue_id)
    except IssueNotFoundException:
        print(messages.issue_not_found.format(id=issue_id))
        sys.exit(1)


def _interactive_select_issue_id() -> str:
    issues = issue_service.list_issues(project_id=config.default_project_id)
    if not issues:
        print(messages.no_issues_available)
        sys.exit(1)
    options: list[tuple[str, str]] = [
        (str(i["id"]), f"#{i['id']} {i['subject']}") for i in issues
    ]
    labels = dict(options)
    try:
        issue_id = inline_choice(messages.prompt_select_issue_to_update, options)
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)
    print(messages.update_target_issue.format(label=labels[issue_id]))
    return issue_id


def _interactive_fill_issue_update_args(args: IssueUpdateArgs) -> None:
    # 呼び出し側で issue_id は解決済み
    assert args.issue_id is not None
    current = _read_issue(args.issue_id)
    field_values: list[tuple[str, str]] = [
        ("project", messages.field_project),
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
    # 対象イシューのプロジェクト/トラッカーに該当するカスタムフィールドを選択肢に並べる
    issue_project_id = current.get("project").get("id")
    issue_tracker_id = current.get("tracker").get("id")
    applicable_custom_fields: list[CustomField] = []
    all_custom_fields = fetch_custom_fields()
    if all_custom_fields is not None:
        project_custom_field_ids = fetch_project_issue_custom_field_ids(
            str(issue_project_id)
        )
        tracker_id_str = str(issue_tracker_id)
        applicable_custom_fields = filter_required_issue_custom_fields(
            all_custom_fields,
            project_custom_field_ids,
            tracker_id_str,
        ) + filter_optional_issue_custom_fields(
            all_custom_fields,
            project_custom_field_ids,
            tracker_id_str,
        )
        for custom_field in applicable_custom_fields:
            field_values.append((f"cf_{custom_field['id']}", custom_field["name"]))
    try:
        selected = inline_checkbox(
            messages.prompt_select_update_items,
            field_values,
            initial_value="description",
        )
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)
    if not selected:
        print(messages.canceled_no_items_selected)
        sys.exit(1)
    labels = dict(field_values)
    print(messages.update_items.format(items=", ".join(labels[v] for v in selected)))
    try:
        if "project" in selected:
            args.project_id = prompt_project(default=str(issue_project_id))
        # 移動する場合、トラッカーなどの選択肢は移動先プロジェクトのものを出す
        project_id = args.project_id or (current.get("project") or {}).get("id")
        if "tracker" in selected:
            if not project_id:
                print(messages.canceled_no_project)
                sys.exit(1)
            try:
                project = project_service.read_project(
                    str(project_id), include="trackers"
                )
            except ProjectNotFoundException:
                print(messages.project_not_found.format(id=project_id))
                sys.exit(1)
            except ProjectPermissionDeniedException:
                print(messages.project_permission_denied.format(id=project_id))
                sys.exit(1)
            trackers = project.get("trackers") or []
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
            if not project_id:
                print(messages.canceled_no_project)
                sys.exit(1)
            current_assignee_id = (current.get("assigned_to") or {}).get("id")
            default_assignee = (
                str(current_assignee_id) if current_assignee_id is not None else ""
            )
            args.assigned_to_id = prompt_assignee(
                str(project_id), default=default_assignee
            )
        if "fixed_version" in selected:
            if not project_id:
                print(messages.canceled_no_project)
                sys.exit(1)
            current_version_id = (current.get("fixed_version") or {}).get("id")
            default_version = (
                str(current_version_id) if current_version_id is not None else ""
            )
            args.fixed_version_id = prompt_fixed_version(
                str(project_id), default=default_version
            )
        if "start_date" in selected:
            args.start_date = prompt_start_date(
                current.get("start_date") or date.today().isoformat()
            )
        if "due_date" in selected:
            effective_start = (
                args.start_date
                if "start_date" in selected
                else current.get("start_date")
            )
            args.due_date = prompt_due_date(
                parse_iso_date(effective_start),
                default=current.get("due_date") or date.today().isoformat(),
            )
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
            estimated_hours = prompt_estimated_hours(default_estimated)
            if estimated_hours is not None:
                args.estimated_hours = estimated_hours
                print(messages.estimated_hours_label.format(value=estimated_hours))
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
            args.spent_on = (
                prompt(
                    messages.prompt_spent_on,
                    validator=DateValidator(allow_empty=True),
                    key_bindings=date_key_bindings(),
                ).strip()
                or None
            )
            args.time_comments = prompt(messages.prompt_time_comments).strip() or None
        # 選択されたカスタムフィールドの値を入力する
        current_cf_values = {
            custom_field["id"]: custom_field.get("value")
            for custom_field in (current.get("custom_fields") or [])
        }
        added_custom_fields: list[str] = []
        for custom_field in applicable_custom_fields:
            if f"cf_{custom_field['id']}" not in selected:
                continue
            custom_field_for_prompt = custom_field
            current_value = current_cf_values.get(custom_field["id"])
            # 文字列・複数選択(リスト)いずれの現在値も入力のデフォルトとして提示する
            if current_value:
                custom_field_for_prompt = cast(
                    CustomField, {**custom_field, "default_value": current_value}
                )
            custom_field_value = prompt_custom_field_value(
                custom_field_for_prompt, str(issue_project_id)
            )
            if custom_field_value is SKIP_UNSUPPORTED_FIELD:
                continue
            if isinstance(custom_field_value, list):
                for v in custom_field_value:
                    added_custom_fields.append(f"{custom_field['id']}={v}")
            else:
                added_custom_fields.append(f"{custom_field['id']}={custom_field_value}")
        if added_custom_fields:
            if args.custom_fields:
                args.custom_fields = (
                    args.custom_fields + "," + ",".join(added_custom_fields)
                )
            else:
                args.custom_fields = ",".join(added_custom_fields)
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)


def _update_issue(args: IssueUpdateArgs, description: str | None) -> None:
    """イシューを更新し、結果を標準出力に出す。HTTP エラーは exit 1。"""
    # 呼び出し側で issue_id は解決済み
    assert args.issue_id is not None
    try:
        issue_service.update_issue(
            issue_id=args.issue_id,
            project_id=args.project_id,
            subject=args.subject,
            description=description or None,
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
            custom_fields=parse_custom_fields(args.custom_fields)
            if args.custom_fields
            else None,
            attachments=args.attach,
        )
    except ProjectNotFoundException:
        print(messages.project_not_found.format(id=args.project_id))
        sys.exit(1)
    except LocalFileNotFoundException as e:
        print(messages.file_not_found.format(path=e.path))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.issue_update_failed)
        sys.exit(1)
    print(
        messages.issue_updated.format(url=issue_service.issue_url(args.issue_id)),
    )


def _add_watcher(issue_id: str, user_id: int) -> None:
    """ウォッチャーを追加し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        issue_service.add_watcher(issue_id, user_id)
    except IssueNotFoundException:
        print(messages.issue_not_found.format(id=issue_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.watcher_add_failed)
        sys.exit(1)
    print(messages.watcher_added.format(issue_id=issue_id, user_id=user_id))


def _remove_watcher(issue_id: str, user_id: int) -> None:
    """ウォッチャーを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        issue_service.remove_watcher(issue_id, user_id)
    except WatcherNotFoundException:
        print(
            messages.issue_or_user_not_found.format(issue_id=issue_id, user_id=user_id)
        )
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.watcher_remove_failed)
        sys.exit(1)
    print(messages.watcher_removed.format(issue_id=issue_id, user_id=user_id))


def _create_relation(issue_id: str, issue_to_id: str, relation_type: str) -> None:
    """関係性を作成し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        issue_relation_service.create_relation(
            issue_id=issue_id,
            issue_to_id=issue_to_id,
            relation_type=relation_type,
        )
    except RelatedIssueNotFoundException as e:
        print(messages.related_issue_not_found.format(id=e.issue_to_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.relation_create_failed)
        sys.exit(1)
    print(
        messages.relation_created.format(
            from_id=issue_id, type=relation_type, to_id=issue_to_id
        )
    )


def _delete_relation(issue_id: str, issue_to_id: str) -> None:
    """イシュー間の関係性を削除し、結果を標準出力に出す。対象が無ければ exit 1。"""
    try:
        relation = issue_relation_service.delete_relation(
            issue_id=issue_id,
            issue_to_id=issue_to_id,
        )
    except RelationBetweenNotFoundException:
        print(
            messages.relation_between_not_found.format(
                from_id=issue_id, to_id=issue_to_id
            )
        )
        sys.exit(1)
    except RelationNotFoundException as e:
        # 一覧を引いてから DELETE するまでの間に消えていた場合
        print(messages.relation_not_found.format(id=e.relation_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.relation_delete_failed)
        return
    print(
        messages.relation_deleted.format(
            from_id=relation["issue_id"],
            type=relation["relation_type"],
            to_id=relation["issue_to_id"],
        )
    )


def handle_issue_update(args: argparse.Namespace) -> None:
    """argparse アダプタ。Namespace を読むのはここまでに閉じる。"""
    _run_issue_update(IssueUpdateArgs.from_namespace(args))


def update_issue_interactively(issue_id: str | None = None) -> None:
    """更新項目を対話で選ばせる入口。TUI から使う。"""
    _run_issue_update(IssueUpdateArgs(issue_id=issue_id))


def _run_issue_update(args: IssueUpdateArgs) -> None:
    if not args.issue_id:
        args.issue_id = _interactive_select_issue_id()
    no_args_provided = not (
        args.project_id
        or args.subject
        or args.description is not None
        or args.tracker_id
        or args.status_id
        or args.priority_id
        or args.assigned_to_id is not None
        or args.fixed_version_id is not None
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
        current = _read_issue(args.issue_id)
        description = open_editor(current.get("description") or "")
    # 空の説明は「変更しない」扱いなので更新対象から外す
    should_update_issue = (
        args.project_id
        or args.subject
        or description
        or args.tracker_id
        or args.status_id
        or args.priority_id
        or args.assigned_to_id is not None
        or args.fixed_version_id is not None
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
        try:
            _update_issue(args, description)
        except Exception:
            save_body_on_failure(description)
            raise
    if args.delete_relation:
        if not args.relate_to:
            print(messages.delete_relation_requires_to)
            sys.exit(1)
        _delete_relation(
            issue_id=args.issue_id,
            issue_to_id=args.relate_to,
        )
    elif args.relate and args.relate_to:
        _create_relation(
            issue_id=args.issue_id,
            issue_to_id=args.relate_to,
            relation_type=args.relate,
        )
    elif args.relate or args.relate_to:
        print(messages.relate_and_to_required)
        sys.exit(1)
    if should_create_time_entry:
        create_time_entry(
            issue_id=args.issue_id,
            hours=args.hours,
            activity_id=args.activity_id,
            spent_on=args.spent_on,
            comments=args.time_comments,
        )
    for user_id in args.add_watcher_ids or []:
        _add_watcher(args.issue_id, user_id)
    for user_id in args.remove_watcher_ids or []:
        _remove_watcher(args.issue_id, user_id)
    should_update_watchers = bool(args.add_watcher_ids or args.remove_watcher_ids)
    if (
        not should_update_issue
        and not should_update_issue_relation
        and not should_create_time_entry
        and not should_update_watchers
    ):
        print(messages.update_canceled_no_changes)
        sys.exit(1)
