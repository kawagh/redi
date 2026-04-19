import argparse

from prompt_toolkit import prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPress
from prompt_toolkit.keys import Keys
from prompt_toolkit.shortcuts import choice
from prompt_toolkit.validation import Validator

from redi.cli._common import resolve_alias
from redi.config import default_project_id
from redi.api.version import (
    create_version,
    fetch_version,
    fetch_versions,
    list_versions,
    read_version,
    update_version,
)


def add_version_parser(subparsers: argparse._SubParsersAction) -> None:
    v_parser = subparsers.add_parser("version", aliases=["v"], help="バージョン一覧")
    v_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    v_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    v_subparsers = v_parser.add_subparsers(dest="version_command")
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


def _make_choice_key_bindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add("c-p")
    def _move_up(event):
        event.app.key_processor.feed(KeyPress(Keys.Up))

    @kb.add("c-n")
    def _move_down(event):
        event.app.key_processor.feed(KeyPress(Keys.Down))

    return kb


def _interactive_select_version_id(project_id: str) -> str:
    versions = fetch_versions(project_id)
    if not versions:
        print("選択可能なバージョンがありません")
        exit(1)
    options: list[tuple[str, str]] = [
        (str(v["id"]), f"{v['id']} {v['name']} ({v['status']})") for v in versions
    ]
    try:
        return choice(
            "更新するバージョンを選択",
            options=options,
            key_bindings=_make_choice_key_bindings(),
        )
    except KeyboardInterrupt:
        print("キャンセルしました")
        exit(1)


def _interactive_fill_version_update_args(args: argparse.Namespace) -> None:
    current = fetch_version(args.version_id)
    skip_label = "変更しない"
    try:
        name = prompt(
            f"バージョン名（現在: {current.get('name') or '未設定'}、空で変更しない）: "
        ).strip()
        if name:
            args.name = name

        status_options: list[tuple[str | None, str]] = [
            (None, skip_label),
            ("open", "open"),
            ("locked", "locked"),
            ("closed", "closed"),
        ]
        status = choice(
            f"ステータス（現在: {current.get('status') or '未設定'}）",
            options=status_options,
            default=None,
            key_bindings=_make_choice_key_bindings(),
        )
        if status:
            args.status = status

        due_date = prompt(
            f"期日（現在: {current.get('due_date') or '未設定'}、YYYY-MM-DD、空で変更しない）: "
        ).strip()
        if due_date:
            args.due_date = due_date

        description = prompt(
            f"説明（現在: {current.get('description') or '未設定'}、空で変更しない）: "
        ).strip()
        if description:
            args.description = description

        sharing_options: list[tuple[str | None, str]] = [
            (None, skip_label),
            ("none", "none"),
            ("descendants", "descendants"),
            ("hierarchy", "hierarchy"),
            ("tree", "tree"),
            ("system", "system"),
        ]
        sharing = choice(
            f"共有設定（現在: {current.get('sharing') or '未設定'}）",
            options=sharing_options,
            default=None,
            key_bindings=_make_choice_key_bindings(),
        )
        if sharing:
            args.sharing = sharing
    except (KeyboardInterrupt, EOFError):
        print("キャンセルしました")
        exit(1)


def _interactive_create_version(project_id: str, args: argparse.Namespace) -> None:
    non_empty_validator = Validator.from_callable(
        lambda text: len(text.strip()) > 0,
        error_message="入力してください",
    )
    try:
        name = prompt("バージョン名: ", validator=non_empty_validator).strip()
    except (KeyboardInterrupt, EOFError):
        print("キャンセルしました")
        exit(1)

    try:
        due_date = prompt("期日（YYYY-MM-DD、省略可）: ").strip() or None
    except (KeyboardInterrupt, EOFError):
        print("キャンセルしました")
        exit(1)

    try:
        description = prompt("説明（省略可）: ").strip() or None
    except (KeyboardInterrupt, EOFError):
        print("キャンセルしました")
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
        print("キャンセルしました")
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
            print("project_idを指定するか、default_project_idを設定してください")
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
    elif cmd == "update":
        if not args.version_id:
            project_id = args.project_id or default_project_id
            if not project_id:
                print("project_idを指定するか、default_project_idを設定してください")
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
    else:
        project_id = args.project_id or default_project_id
        if not project_id:
            print("project_idを指定するか、default_project_idを設定してください")
            exit(1)
        list_versions(project_id, full=args.full)
