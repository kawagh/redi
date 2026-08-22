"""`redi project` の表示整形と入力の検証。

取得や更新の手順は `service.project_service` に任せ、ここでは print と sys.exit を担当する。
"""

import argparse
import json
import sys
import webbrowser

import requests

from redi.api.exceptions import (
    ProjectNotFoundException,
    ProjectPermissionDeniedException,
    print_http_error_body,
)
from redi.api.project import Project
from redi.api.tracker import fetch_trackers
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete_with_identifier
from redi.cli.editor import open_editor, shorten_to_oneline
from redi.cli.interactive import prompt
from redi.cli.picker import inline_checkbox, inline_choice
from redi.cli.shared_options import full_option_parser
from redi.cli.validator import ProjectIdentifierValidator, RequiredValidator
from redi.i18n import messages
from redi.service import project_service


def _list_projects(full: bool = False) -> None:
    """プロジェクト一覧を1行ずつ出す。full=True では取得した JSON をそのまま出す。"""
    projects = project_service.list_projects()
    if full:
        print(json.dumps(projects, ensure_ascii=False))
        return
    for project in projects:
        print(f"{project['id']} {project['name']}")


def _view_project(
    project_id: str, include: str = "", full: bool = False, web: bool = False
) -> None:
    """プロジェクトの詳細を標準出力に出す。存在しない場合は exit 1。"""
    if web:
        url = project_service.project_url(project_id)
        print(url)
        webbrowser.open(url)
        return
    project = _read_project_or_exit(project_id, include=include)
    if full:
        print(json.dumps(project, ensure_ascii=False))
        return
    print("\n".join(format_project_detail(project)))


def _read_project_or_exit(project_id: str, include: str = "") -> Project:
    """プロジェクトを取得する。存在しない・参照できない場合は exit 1。"""
    try:
        return project_service.read_project(project_id, include=include)
    except ProjectNotFoundException:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except ProjectPermissionDeniedException:
        print(messages.project_permission_denied.format(id=project_id))
        sys.exit(1)


def format_project_detail(project: Project) -> list[str]:
    """プロジェクトの詳細表示を行のリストに整形する。"""
    lines = []
    lines.append(f"{project['id']} {project['name']} ({project['identifier']})")
    description = project.get("description")
    if description:
        lines.append("")
        lines.append(description)
    parent = project.get("parent")
    if parent:
        lines.append("")
        lines.append(
            messages.label_parent_project.format(
                id=parent.get("id"), name=parent.get("name", "")
            )
        )
    trackers = project.get("trackers") or []
    if trackers:
        lines.append("")
        lines.append(messages.label_trackers_header)
        for t in trackers:
            lines.append(f"  {t['id']} {t['name']}")
    issue_categories = project.get("issue_categories") or []
    if issue_categories:
        lines.append("")
        lines.append(messages.label_issue_categories_header)
        for c in issue_categories:
            lines.append(f"  {c['id']} {c['name']}")
    enabled_modules = project.get("enabled_modules") or []
    if enabled_modules:
        lines.append("")
        lines.append(messages.label_enabled_modules_header)
        for m in enabled_modules:
            lines.append(f"  {m.get('name')}")
    return lines


def _create_project(
    name: str,
    identifier: str,
    description: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    tracker_ids: list[int] | None = None,
) -> None:
    """プロジェクトを作成し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        created = project_service.create_project(
            name=name,
            identifier=identifier,
            description=description,
            is_public=is_public,
            parent_id=parent_id,
            tracker_ids=tracker_ids,
        )
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        sys.exit(1)
    print(f"{created['id']} {created['name']} ({created['identifier']})")


def _update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    tracker_ids: list[int] | None = None,
) -> None:
    """プロジェクトを更新し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        project_service.update_project(
            project_id,
            name=name,
            description=description,
            is_public=is_public,
            parent_id=parent_id,
            tracker_ids=tracker_ids,
        )
    except ProjectNotFoundException:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.project_update_failed)
        sys.exit(1)
    print(messages.project_updated.format(id=project_id))


def _archive_project(project_id: str) -> None:
    """プロジェクトをアーカイブし、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        project_service.archive_project(project_id)
    except ProjectNotFoundException:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.project_archive_failed)
        sys.exit(1)
    print(messages.project_archived.format(id=project_id))


def _unarchive_project(project_id: str) -> None:
    """プロジェクトのアーカイブを解除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        project_service.unarchive_project(project_id)
    except ProjectNotFoundException:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.project_unarchive_failed)
        sys.exit(1)
    print(messages.project_unarchived.format(id=project_id))


def _delete_project(project_id: str) -> None:
    """プロジェクトを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        project_service.delete_project(project_id)
    except ProjectNotFoundException:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.project_delete_failed)
        sys.exit(1)
    print(messages.project_deleted.format(id=project_id))


def _interactive_select_parent_id(current: str | None) -> str | None:
    """親プロジェクトを一覧から選ばせる。「なし」を選んだ場合は None を返す。"""
    options: list[tuple[str, str]] = [
        ("", messages.prompt_select_parent_project_none)
    ] + [
        (str(project["id"]), f"{project['id']} {project['name']}")
        for project in project_service.list_projects()
    ]
    labels = dict(options)
    selected = inline_choice(
        messages.prompt_select_parent_project, options, default=current
    )
    print(
        messages.prompt_field_value.format(
            name=messages.field_parent_project, value=labels[selected]
        )
    )
    return selected or None


def _interactive_select_tracker_ids(current: str | None) -> str | None:
    """トラッカーを複数選ばせ、カンマ区切りの id 文字列を返す。"""
    trackers = fetch_trackers()
    options: list[tuple[str, str]] = [(str(t["id"]), t["name"]) for t in trackers]
    labels = dict(options)
    selected = inline_checkbox(
        messages.prompt_select_trackers,
        options,
        initial_checked=current.split(",") if current else None,
    )
    if not selected:
        return None
    print(
        messages.prompt_field_value.format(
            name=messages.field_trackers,
            value=", ".join(labels[v] for v in selected),
        )
    )
    return ",".join(selected)


def _interactive_fill_optional_create_fields(args: argparse.Namespace) -> None:
    """アクションメニューで「任意項目を入力する」を選んだときの入力フロー。

    入力結果は argparse が渡す形式のまま args へ書き戻し、
    送信前の変換は `handle_project` の一箇所に閉じる。
    """
    field_options: list[tuple[str, str]] = [
        ("description", messages.field_description),
        ("is_public", messages.field_is_public),
        ("parent_id", messages.field_parent_project),
        ("tracker_ids", messages.field_trackers),
    ]
    try:
        selected = inline_checkbox(
            messages.prompt_select_create_optional_items, field_options
        )
        if not selected:
            return
        if "description" in selected:
            args.description = open_editor(initial_text=args.description or "")
            if args.description:
                print(
                    messages.prompt_field_value.format(
                        name=messages.field_description,
                        value=shorten_to_oneline(args.description),
                    )
                )
        if "is_public" in selected:
            is_public_options: list[tuple[str, str]] = [
                ("true", messages.label_project_public),
                ("false", messages.label_project_private),
            ]
            labels = dict(is_public_options)
            args.is_public = inline_choice(
                messages.prompt_select_is_public,
                is_public_options,
                default=args.is_public,
            )
            print(
                messages.prompt_field_value.format(
                    name=messages.field_is_public, value=labels[args.is_public]
                )
            )
        if "parent_id" in selected:
            args.parent_id = _interactive_select_parent_id(args.parent_id)
        if "tracker_ids" in selected:
            args.tracker_ids = _interactive_select_tracker_ids(args.tracker_ids)
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)


def _interactive_fill_create_args(args: argparse.Namespace) -> None:
    """`project create` の必須項目を対話で埋め、送信前に任意項目の入力機会を挟む。"""
    try:
        if args.name is None:
            args.name = prompt(
                messages.prompt_project_name, validator=RequiredValidator()
            ).strip()
        if args.identifier is None:
            args.identifier = prompt(
                messages.prompt_project_identifier,
                default=project_service.suggest_identifier(args.name),
                validator=ProjectIdentifierValidator(),
            ).strip()
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)
    action_options: list[tuple[str, str]] = [
        ("submit", messages.action_submit),
        ("optional", messages.action_fill_optional),
    ]
    while True:
        try:
            action = inline_choice(messages.prompt_what_next, action_options)
        except (KeyboardInterrupt, EOFError):
            print(messages.canceled)
            sys.exit(1)
        if action != "optional":
            return
        _interactive_fill_optional_create_fields(args)


def add_project_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    p_parser = subparsers.add_parser(
        "project",
        aliases=["p"],
        help=messages.arg_help_project_command,
        parents=[*parents, full_option_parser()],
    )
    p_subparsers = p_parser.add_subparsers(dest="project_command")
    p_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_project_list,
        parents=[*parents, full_option_parser(postfix=True)],
    )
    p_view_parser = p_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_project_view, parents=parents
    )
    p_view_parser.add_argument("project_id", help=messages.arg_help_project_view_id)
    p_view_parser.add_argument(
        "--include",
        help=messages.arg_help_project_include,
    )
    p_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    p_view_parser.add_argument(
        "--web", "-w", action="store_true", help=messages.arg_help_open_web
    )
    p_create_parser = p_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_project_create, parents=parents
    )
    p_create_parser.add_argument(
        "name", nargs="?", help=messages.arg_help_project_name_arg
    )
    p_create_parser.add_argument(
        "identifier", nargs="?", help=messages.arg_help_project_identifier
    )
    p_create_parser.add_argument(
        "--description", "-d", help=messages.arg_help_description
    )
    p_create_parser.add_argument(
        "--is_public",
        choices=["true", "false"],
        help=messages.arg_help_project_is_public,
    )
    p_create_parser.add_argument("--parent_id", help=messages.arg_help_parent_id)
    p_create_parser.add_argument("--tracker_ids", help=messages.arg_help_tracker_ids)
    p_delete_parser = p_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_project_delete, parents=parents
    )
    p_delete_parser.add_argument("project_id", help=messages.arg_help_project_delete_id)
    p_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )
    p_update_parser = p_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_project_update, parents=parents
    )
    p_update_parser.add_argument("project_id", help=messages.arg_help_project_update_id)
    p_update_parser.add_argument("--name", "-n", help=messages.arg_help_project_name)
    p_update_parser.add_argument(
        "--description", "-d", help=messages.arg_help_description
    )
    p_update_parser.add_argument(
        "--is_public",
        choices=["true", "false"],
        help=messages.arg_help_project_is_public,
    )
    p_update_parser.add_argument("--parent_id", help=messages.arg_help_parent_id)
    p_update_parser.add_argument("--tracker_ids", help=messages.arg_help_tracker_ids)
    p_update_parser.add_argument(
        "--archive",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=messages.arg_help_project_archive,
    )


def handle_project(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.project_command)
    if cmd == "view":
        _view_project(
            args.project_id,
            include=args.include or "",
            full=args.full,
            web=args.web,
        )
    elif cmd == "create":
        if args.name is None or args.identifier is None:
            _interactive_fill_create_args(args)
        is_public = None
        if args.is_public is not None:
            is_public = args.is_public == "true"
        tracker_ids = None
        if args.tracker_ids:
            tracker_ids = [int(x) for x in args.tracker_ids.split(",")]
        _create_project(
            name=args.name,
            identifier=args.identifier,
            description=args.description,
            is_public=is_public,
            parent_id=args.parent_id,
            tracker_ids=tracker_ids,
        )
    elif cmd == "delete":
        if not args.yes:
            project = _read_project_or_exit(args.project_id)
            summary = (
                messages.delete_target_project.format(
                    id=project["id"],
                    name=project["name"],
                    identifier=project["identifier"],
                )
                + "\n"
                + messages.delete_project_warning
            )
            confirm_delete_with_identifier(
                summary, project["identifier"], messages.label_project_identifier
            )
        _delete_project(args.project_id)
    elif cmd == "update":
        is_public = None
        if args.is_public is not None:
            is_public = args.is_public == "true"
        tracker_ids = None
        if args.tracker_ids:
            tracker_ids = [int(x) for x in args.tracker_ids.split(",")]
        should_update = (
            args.name is not None
            or args.description is not None
            or is_public is not None
            or args.parent_id is not None
            or tracker_ids is not None
        )
        if should_update:
            _update_project(
                args.project_id,
                name=args.name,
                description=args.description,
                is_public=is_public,
                parent_id=args.parent_id,
                tracker_ids=tracker_ids,
            )
        if args.archive is True:
            _archive_project(args.project_id)
        elif args.archive is False:
            _unarchive_project(args.project_id)
        elif not should_update:
            print(messages.update_canceled)
            sys.exit()
    elif cmd == "list" or cmd is None:
        _list_projects(full=args.full)
