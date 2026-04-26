import argparse

from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.validation import Validator

from redi.cli._common import (
    confirm_delete,
    inline_checkbox,
    inline_choice,
    resolve_alias,
)
from redi.config import default_project_id
from redi.i18n import messages
from redi.api.version import (
    create_version,
    delete_version,
    fetch_version,
    fetch_versions,
    list_versions,
    read_version,
    update_version,
)


def add_version_parser(subparsers: argparse._SubParsersAction) -> None:
    v_parser = subparsers.add_parser(
        "version",
        aliases=["v"],
        help="list(l): 一覧, view(v): 詳細, create(c): 作成, update(u): 更新, delete(d): 削除",
    )
    v_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    v_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    v_subparsers = v_parser.add_subparsers(dest="version_command")
    v_subparsers.add_parser("list", aliases=["l"], help="バージョン一覧")
    v_view_parser = v_subparsers.add_parser(
        "view", aliases=["v"], help="バージョン詳細"
    )
    v_view_parser.add_argument("version_id", help="バージョンID")
    v_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    v_view_parser.add_argument(
        "--web", "-w", action="store_true", help="ブラウザでRedmineのページを開く"
    )
    v_create_parser = v_subparsers.add_parser(
        "create", aliases=["c"], help="バージョン作成"
    )
    v_create_parser.add_argument("name", nargs="?", default=None, help="バージョン名")
    v_create_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    v_create_parser.add_argument(
        "--status", choices=["open", "locked", "closed"], help="ステータス"
    )
    v_create_parser.add_argument("--due_date", help="期日（YYYY-MM-DD）")
    v_create_parser.add_argument("--description", "-d", help="説明")
    v_create_parser.add_argument(
        "--sharing",
        choices=["none", "descendants", "hierarchy", "tree", "system"],
        help="共有設定",
    )
    v_delete_parser = v_subparsers.add_parser(
        "delete", aliases=["d"], help="バージョン削除"
    )
    v_delete_parser.add_argument("version_id", help="バージョンID")
    v_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help="確認プロンプトをスキップ"
    )
    v_update_parser = v_subparsers.add_parser(
        "update", aliases=["u"], help="バージョン更新"
    )
    v_update_parser.add_argument(
        "version_id", nargs="?", help="バージョンID（省略で対話的に選択）"
    )
    v_update_parser.add_argument("--name", "-n", help="バージョン名")
    v_update_parser.add_argument(
        "--status", choices=["open", "locked", "closed"], help="ステータス"
    )
    v_update_parser.add_argument("--due_date", help="期日（YYYY-MM-DD）")
    v_update_parser.add_argument("--description", "-d", help="説明")
    v_update_parser.add_argument(
        "--sharing",
        choices=["none", "descendants", "hierarchy", "tree", "system"],
        help="共有設定",
    )


def _interactive_select_version_id(project_id: str) -> str:
    versions = fetch_versions(project_id)
    if not versions:
        print(messages.no_versions_available)
        exit(1)
    options: list[tuple[str, str]] = [
        (str(v["id"]), f"{v['id']} {v['name']} ({v['status']})") for v in versions
    ]
    labels = dict(options)
    try:
        selected = inline_choice("更新するバージョンを選択", options)
    except KeyboardInterrupt:
        print(messages.canceled)
        exit(1)
    print(messages.update_target_version.format(label=labels[selected]))
    return selected


def _interactive_fill_version_update_args(args: argparse.Namespace) -> None:
    current = fetch_version(args.version_id)
    field_values: list[tuple[str, str]] = [
        ("name", "バージョン名 (name)"),
        ("status", "ステータス (status)"),
        ("due_date", "期日 (due_date)"),
        ("description", "説明 (description)"),
        ("sharing", "共有設定 (sharing)"),
    ]
    try:
        selected = inline_checkbox(
            "更新する項目を選択 (Spaceで選択、Enterで確定)", field_values
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
        if "name" in selected:
            args.name = prompt(
                "バージョン名: ", default=current.get("name", "")
            ).strip()

        if "status" in selected:
            status_options: list[tuple[str, str]] = [
                ("open", "open"),
                ("locked", "locked"),
                ("closed", "closed"),
            ]
            args.status = inline_choice(
                "ステータス", status_options, default=current.get("status", "open")
            )
            print(messages.status_label.format(value=args.status))

        if "due_date" in selected:
            args.due_date = prompt(
                "期日（YYYY-MM-DD）: ", default=current.get("due_date", "")
            ).strip()

        if "description" in selected:
            args.description = prompt(
                "説明: ", default=current.get("description", "")
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
                "共有設定",
                sharing_options,
                default=current.get("sharing", "none"),
            )
            print(messages.sharing_label.format(value=args.sharing))
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)


def _interactive_create_version(project_id: str, args: argparse.Namespace) -> None:
    non_empty_validator = Validator.from_callable(
        lambda text: len(text.strip()) > 0,
        error_message="入力してください",
    )
    try:
        name = prompt("バージョン名: ", validator=non_empty_validator).strip()
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)

    try:
        due_date = prompt("期日（YYYY-MM-DD、省略可）: ").strip() or None
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)

    try:
        description = prompt("説明（省略可）: ").strip() or None
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        exit(1)

    sharing_options: list[tuple[str, str]] = [
        ("none", "none (共有しない)"),
        ("descendants", "descendants (子プロジェクトと共有)"),
        ("hierarchy", "hierarchy (階層内で共有)"),
        ("tree", "tree (ツリー全体で共有)"),
        ("system", "system (システム全体で共有)"),
    ]
    choice_kb = KeyBindings()

    @choice_kb.add("c-p")
    def _move_up(event):
        event.app.key_processor.feed(KeyPress(Keys.Up))

    @choice_kb.add("c-n")
    def _move_down(event):
        event.app.key_processor.feed(KeyPress(Keys.Down))

    try:
        sharing_input = choice(
            "共有設定",
            options=sharing_options,
            default="none",
            key_bindings=choice_kb,
        )
    except KeyboardInterrupt:
        print(messages.canceled)
        exit(1)
    sharing = sharing_input if sharing_input != "none" else None

    create_version(
        project_id=project_id,
        name=name,
        due_date=due_date,
        description=description,
        sharing=sharing,
    )


def handle_version(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.version_command)
    if cmd == "view":
        read_version(args.version_id, full=args.full, web=args.web)
    elif cmd == "create":
        project_id = args.project_id or default_project_id
        if not project_id:
            print(messages.project_id_required)
            exit(1)
        if args.name is None:
            _interactive_create_version(project_id, args)
        else:
            create_version(
                project_id=project_id,
                name=args.name,
                status=args.status,
                due_date=args.due_date,
                description=args.description,
                sharing=args.sharing,
            )
    elif cmd == "delete":
        if not args.yes:
            version = fetch_version(args.version_id)
            confirm_delete(f"削除するバージョン: {version['id']} {version['name']}")
        delete_version(args.version_id)
    elif cmd == "update":
        if not args.version_id:
            project_id = args.project_id or default_project_id
            if not project_id:
                print(messages.project_id_required)
                exit(1)
            args.version_id = _interactive_select_version_id(project_id)
        no_args_provided = not (
            args.name
            or args.status
            or args.due_date
            or args.description
            or args.sharing
        )
        if no_args_provided:
            _interactive_fill_version_update_args(args)
        update_version(
            version_id=args.version_id,
            name=args.name,
            status=args.status,
            due_date=args.due_date,
            description=args.description,
            sharing=args.sharing,
        )
    elif cmd == "list" or cmd is None:
        project_id = args.project_id or default_project_id
        if not project_id:
            print(messages.project_id_required)
            exit(1)
        list_versions(project_id, full=args.full)
