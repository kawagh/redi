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
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete_with_identifier
from redi.cli.shared_options import full_option_parser
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
    p_create_parser.add_argument("name", help=messages.arg_help_project_name)
    p_create_parser.add_argument(
        "identifier", help=messages.arg_help_project_identifier
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
