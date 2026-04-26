import argparse

from redi.cli._common import resolve_alias
from redi.config import (
    create_profile,
    set_default_profile,
    show_config,
    update_config,
)
from redi.i18n import messages


def add_config_parser(subparsers: argparse._SubParsersAction) -> None:
    c_parser = subparsers.add_parser(
        "config", aliases=["c"], help="設定表示/更新/プロファイル作成"
    )
    c_parser.add_argument("--full", action="store_true", help="全プロファイルを表示")
    c_subparsers = c_parser.add_subparsers(dest="config_command")
    c_update_parser = c_subparsers.add_parser("update", aliases=["u"], help="設定更新")
    c_update_parser.add_argument(
        "profile_name",
        nargs="?",
        help="更新対象のプロファイル名（省略時はdefault_profile）",
    )
    c_update_parser.add_argument("--project_id", help="デフォルトプロジェクトIDを設定")
    c_update_parser.add_argument("--wiki_project_id", help="Wiki用プロジェクトIDを設定")
    c_update_parser.add_argument("--editor", help="エディタを設定")
    c_update_parser.add_argument("--api_key", help="Redmine APIキーを設定")
    c_update_parser.add_argument("--url", help="Redmine URLを設定")
    c_update_parser.add_argument(
        "--default_profile", help="デフォルトプロファイルを設定"
    )
    c_create_parser = c_subparsers.add_parser(
        "create", aliases=["c"], help="プロファイル作成"
    )
    c_create_parser.add_argument("profile_name", help="作成するプロファイル名")
    c_create_parser.add_argument("--url", help="Redmine URL")
    c_create_parser.add_argument("--api_key", help="Redmine APIキー")
    c_create_parser.add_argument("--project_id", help="デフォルトプロジェクトID")
    c_create_parser.add_argument("--wiki_project_id", help="Wiki用プロジェクトID")
    c_create_parser.add_argument("--editor", help="エディタ")
    c_create_parser.add_argument(
        "--set_default",
        action="store_true",
        help="作成したプロファイルをdefault_profileに設定",
    )


def handle_config(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.config_command)
    if cmd == "create":
        result = create_profile(
            profile_name=args.profile_name,
            redmine_url=args.url,
            redmine_api_key=args.api_key,
            default_project_id=args.project_id,
            wiki_project_id=args.wiki_project_id,
            editor=args.editor,
        )
        if not result.created:
            exit(1)
        print(messages.profile_created.format(name=args.profile_name))
        if result.set_as_default:
            print(messages.default_profile_set.format(name=args.profile_name))
        elif args.set_default and set_default_profile(args.profile_name):
            print(messages.default_profile_set.format(name=args.profile_name))
        return
    if cmd != "update":
        show_config(full=args.full)
        return
    updated = False
    profile = args.profile_name
    profile_suffix = f"（profile: {profile}）" if profile else ""
    if args.project_id:
        update_config("default_project_id", args.project_id, profile)
        print(
            messages.default_project_id_set.format(
                value=args.project_id, suffix=profile_suffix
            )
        )
        updated = True
    if args.wiki_project_id:
        update_config("wiki_project_id", args.wiki_project_id, profile)
        print(
            messages.wiki_project_id_set.format(
                value=args.wiki_project_id, suffix=profile_suffix
            )
        )
        updated = True
    if args.editor:
        update_config("editor", args.editor, profile)
        print(messages.editor_set.format(value=args.editor, suffix=profile_suffix))
        updated = True
    if args.api_key:
        update_config("redmine_api_key", args.api_key, profile)
        print(messages.redmine_api_key_set.format(suffix=profile_suffix))
        updated = True
    if args.url:
        update_config("redmine_url", args.url, profile)
        print(messages.redmine_url_set.format(value=args.url, suffix=profile_suffix))
        updated = True
    if args.default_profile:
        if set_default_profile(args.default_profile):
            print(messages.default_profile_set.format(name=args.default_profile))
        updated = True
    if not updated:
        show_config()
