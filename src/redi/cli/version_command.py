import argparse
import json
import sys
import webbrowser

import requests
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.validation import Validator

from redi import config
from redi.api.exceptions import ProjectNotFoundException, print_http_error_body
from redi.api.version import Version, VersionNotFoundException
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.interactive import ensure_interactive, prompt
from redi.cli.picker import inline_checkbox, inline_choice
from redi.cli.shared_options import project_option_parser
from redi.i18n import messages
from redi.output import eprint
from redi.service import version_service


def _version_line(version: Version) -> str:
    """一覧・詳細の 1 行目に出すバージョンの要約。"""
    return (
        f"{version['id']} {version['name']} ({version['status']}) "
        f"{version_service.version_url(version['id'])}"
    )


def _read_version_or_exit(version_id: str) -> Version:
    """バージョンを取得する。存在しない場合は exit 1。"""
    try:
        return version_service.read_version(version_id)
    except VersionNotFoundException:
        eprint(messages.version_not_found.format(id=version_id))
        sys.exit(1)


def _read_versions(project_id: str) -> list[Version]:
    """バージョン一覧を取得する。プロジェクトが存在しなければ exit 1。"""
    try:
        return version_service.list_versions(project_id)
    except ProjectNotFoundException:
        eprint(messages.project_not_found.format(id=project_id))
        sys.exit(1)


def _list_versions(project_id: str, full: bool = False) -> None:
    """バージョン一覧を標準出力に出す。full=True では取得した JSON をそのまま出す。"""
    versions = _read_versions(project_id)
    if full:
        print(json.dumps(versions, ensure_ascii=False))
        return
    for version in versions:
        print(_version_line(version))


def _view_version(version_id: str, full: bool = False, web: bool = False) -> None:
    """バージョンの詳細を標準出力に出す。存在しない場合は exit 1。"""
    if web:
        url = version_service.version_url(version_id)
        print(url)
        webbrowser.open(url)
        return
    version = _read_version_or_exit(version_id)
    if full:
        print(json.dumps(version, ensure_ascii=False))
        return

    lines = [_version_line(version)]
    project = version.get("project")
    if project:
        lines.append(
            messages.label_project_field.format(
                id=project.get("id"), name=project.get("name", "")
            )
        )
    if version.get("due_date"):
        lines.append(messages.label_due_date_field.format(value=version["due_date"]))
    if version.get("sharing"):
        lines.append(messages.label_sharing_field.format(value=version["sharing"]))
    if version.get("description"):
        lines.append("")
        lines.append(version["description"])
    print("\n".join(lines))


def _create_version(
    project_id: str,
    name: str,
    status: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
    sharing: str | None = None,
) -> None:
    """バージョンを作成し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        created = version_service.create_version(
            project_id=project_id,
            name=name,
            status=status,
            due_date=due_date,
            description=description,
            sharing=sharing,
        )
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.version_create_failed)
        sys.exit(1)
    print(
        messages.version_created.format(
            id=created["id"],
            name=created["name"],
            url=version_service.version_url(created["id"]),
        )
    )


def _update_version(
    version_id: str,
    name: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
    sharing: str | None = None,
) -> None:
    """バージョンを更新し、結果を標準出力に出す。更新項目が無ければ何もせず終了する。"""
    if not version_service.has_update_fields(
        name=name,
        status=status,
        due_date=due_date,
        description=description,
        sharing=sharing,
    ):
        print(messages.update_canceled)
        sys.exit()
    try:
        version_service.update_version(
            version_id=version_id,
            name=name,
            status=status,
            due_date=due_date,
            description=description,
            sharing=sharing,
        )
    except VersionNotFoundException:
        eprint(messages.version_not_found.format(id=version_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.version_update_failed)
        sys.exit(1)
    print(
        messages.version_updated.format(
            id=version_id, url=version_service.version_url(version_id)
        )
    )


def _delete_version(version_id: str) -> None:
    """バージョンを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        version_service.delete_version(version_id)
    except VersionNotFoundException:
        eprint(messages.version_not_found.format(id=version_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.version_delete_failed)
        sys.exit(1)
    print(messages.version_deleted.format(id=version_id))


def add_version_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    v_parser = subparsers.add_parser(
        "version",
        aliases=["v"],
        help=messages.arg_help_version_command,
        parents=[*parents, project_option_parser()],
    )
    v_subparsers = v_parser.add_subparsers(dest="version_command")
    v_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_version_list,
        parents=[*parents, project_option_parser(postfix=True)],
    )
    v_view_parser = v_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_version_view, parents=parents
    )
    v_view_parser.add_argument("version_id", help=messages.arg_help_version_view_id)
    v_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    v_view_parser.add_argument(
        "--web", "-w", action="store_true", help=messages.arg_help_open_web
    )
    v_create_parser = v_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_version_create, parents=parents
    )
    v_create_parser.add_argument(
        "name", nargs="?", default=None, help=messages.arg_help_version_name_arg
    )
    v_create_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_project_id
    )
    v_create_parser.add_argument(
        "--status",
        choices=["open", "locked", "closed"],
        help=messages.arg_help_version_status,
    )
    v_create_parser.add_argument("--due_date", help=messages.arg_help_version_due_date)
    v_create_parser.add_argument(
        "--description", "-d", help=messages.arg_help_version_description
    )
    v_create_parser.add_argument(
        "--sharing",
        choices=["none", "descendants", "hierarchy", "tree", "system"],
        help=messages.arg_help_version_sharing,
    )
    v_delete_parser = v_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_version_delete, parents=parents
    )
    v_delete_parser.add_argument("version_id", help=messages.arg_help_version_delete_id)
    v_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )
    v_update_parser = v_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_version_update, parents=parents
    )
    v_update_parser.add_argument(
        "version_id", nargs="?", help=messages.arg_help_version_update_id
    )
    v_update_parser.add_argument(
        "--name", "-n", help=messages.arg_help_version_name_opt
    )
    v_update_parser.add_argument(
        "--status",
        choices=["open", "locked", "closed"],
        help=messages.arg_help_version_status,
    )
    v_update_parser.add_argument("--due_date", help=messages.arg_help_version_due_date)
    v_update_parser.add_argument(
        "--description", "-d", help=messages.arg_help_version_description
    )
    v_update_parser.add_argument(
        "--sharing",
        choices=["none", "descendants", "hierarchy", "tree", "system"],
        help=messages.arg_help_version_sharing,
    )


def _interactive_select_version_id(project_id: str) -> str:
    versions = version_service.list_versions(project_id)
    if not versions:
        eprint(messages.no_versions_available)
        sys.exit(1)
    options: list[tuple[str, str]] = [
        (str(v["id"]), f"{v['id']} {v['name']} ({v['status']})") for v in versions
    ]
    labels = dict(options)
    try:
        selected = inline_choice(messages.prompt_select_version_to_update, options)
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)
    print(messages.update_target_version.format(label=labels[selected]))
    return selected


def _interactive_fill_version_update_args(args: argparse.Namespace) -> None:
    current = _read_version_or_exit(args.version_id)
    field_values: list[tuple[str, str]] = [
        ("name", messages.field_version_name),
        ("status", messages.field_status),
        ("due_date", messages.field_due_date),
        ("description", messages.field_description),
        ("sharing", messages.field_sharing),
    ]
    try:
        selected = inline_checkbox(messages.prompt_select_update_items, field_values)
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)
    if not selected:
        eprint(messages.canceled_no_items_selected)
        sys.exit(1)
    labels = dict(field_values)
    print(messages.update_items.format(items=", ".join(labels[v] for v in selected)))
    try:
        if "name" in selected:
            args.name = prompt(
                messages.prompt_version_name, default=current.get("name") or ""
            ).strip()

        if "status" in selected:
            status_options: list[tuple[str, str]] = [
                ("open", "open"),
                ("locked", "locked"),
                ("closed", "closed"),
            ]
            args.status = inline_choice(
                messages.prompt_select_status,
                status_options,
                default=current.get("status") or "open",
            )
            print(messages.status_label.format(value=args.status))

        if "due_date" in selected:
            args.due_date = prompt(
                messages.prompt_due_date_optional,
                # 期日未設定のとき Redmine は null を返すので空文字に寄せる
                default=current.get("due_date") or "",
            ).strip()

        if "description" in selected:
            args.description = prompt(
                messages.prompt_description_optional,
                default=current.get("description") or "",
            ).strip()

        if "sharing" in selected:
            sharing_options: list[tuple[str, str]] = [
                ("none", "none"),
                ("descendants", "descendants"),
                ("hierarchy", "hierarchy"),
                ("tree", "tree"),
                ("system", "system"),
            ]
            args.sharing = inline_choice(
                messages.prompt_select_sharing,
                sharing_options,
                default=current.get("sharing") or "none",
            )
            print(messages.sharing_label.format(value=args.sharing))
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)


def _interactive_create_version(project_id: str, args: argparse.Namespace) -> None:
    non_empty_validator = Validator.from_callable(
        lambda text: len(text.strip()) > 0,
        error_message=messages.error_input_required,
    )
    try:
        name = prompt(
            messages.prompt_version_name, validator=non_empty_validator
        ).strip()
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)

    try:
        due_date = prompt(messages.prompt_due_date_optional).strip() or None
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)

    try:
        description = prompt(messages.prompt_description_optional).strip() or None
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)

    sharing_options: list[tuple[str, str]] = [
        ("none", messages.sharing_none),
        ("descendants", messages.sharing_descendants),
        ("hierarchy", messages.sharing_hierarchy),
        ("tree", messages.sharing_tree),
        ("system", messages.sharing_system),
    ]
    choice_kb = KeyBindings()

    @choice_kb.add("c-p")
    def _move_up(event):
        event.app.key_processor.feed(KeyPress(Keys.Up))

    @choice_kb.add("c-n")
    def _move_down(event):
        event.app.key_processor.feed(KeyPress(Keys.Down))

    ensure_interactive(messages.prompt_select_sharing)
    try:
        sharing_input = choice(
            messages.prompt_select_sharing,
            options=sharing_options,
            default="none",
            key_bindings=choice_kb,
        )
    except (KeyboardInterrupt, EOFError):
        eprint(messages.canceled)
        sys.exit(1)
    sharing = sharing_input if sharing_input != "none" else None

    _create_version(
        project_id=project_id,
        name=name,
        due_date=due_date,
        description=description,
        sharing=sharing,
    )


def handle_version(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.version_command)
    if cmd == "view":
        _view_version(args.version_id, full=args.full, web=args.web)
    elif cmd == "create":
        project_id = args.project_id or config.default_project_id
        if not project_id:
            eprint(messages.project_id_required)
            sys.exit(1)
        if args.name is None:
            _interactive_create_version(project_id, args)
        else:
            _create_version(
                project_id=project_id,
                name=args.name,
                status=args.status,
                due_date=args.due_date,
                description=args.description,
                sharing=args.sharing,
            )
    elif cmd == "delete":
        if not args.yes:
            version = _read_version_or_exit(args.version_id)
            confirm_delete(
                messages.delete_target_version.format(
                    id=version["id"], name=version["name"]
                )
            )
        _delete_version(args.version_id)
    elif cmd == "update":
        if not args.version_id:
            project_id = args.project_id or config.default_project_id
            if not project_id:
                eprint(messages.project_id_required)
                sys.exit(1)
            args.version_id = _interactive_select_version_id(project_id)
        no_args_provided = not version_service.has_update_fields(
            name=args.name,
            status=args.status,
            due_date=args.due_date,
            description=args.description,
            sharing=args.sharing,
        )
        if no_args_provided:
            _interactive_fill_version_update_args(args)
        _update_version(
            version_id=args.version_id,
            name=args.name,
            status=args.status,
            due_date=args.due_date,
            description=args.description,
            sharing=args.sharing,
        )
    elif cmd == "list" or cmd is None:
        project_id = args.project_id or config.default_project_id
        if not project_id:
            eprint(messages.project_id_required)
            sys.exit(1)
        _list_versions(project_id, full=args.full)
