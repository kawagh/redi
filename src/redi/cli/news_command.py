import argparse
import sys

from redi.api.news import (
    create_news,
    delete_news,
    fetch_news,
    list_news,
    read_news,
    update_news,
)
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.editor import open_editor
from redi.config import default_project_id
from redi.i18n import messages


def add_news_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    n_parser = subparsers.add_parser(
        "news", aliases=["n"], help=messages.arg_help_news_command, parents=parents
    )
    n_parser.add_argument("--project_id", "-p", help=messages.arg_help_project_id)
    n_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    n_subparsers = n_parser.add_subparsers(dest="news_command")
    n_subparsers.add_parser(
        "list", aliases=["l"], help=messages.arg_help_news_list, parents=parents
    )

    n_view_parser = n_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_news_view, parents=parents
    )
    n_view_parser.add_argument("news_id", help=messages.arg_help_news_view_id)
    n_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )

    n_create_parser = n_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_news_create, parents=parents
    )
    n_create_parser.add_argument("title", help=messages.arg_help_news_title)
    n_create_parser.add_argument(
        "--project_id",
        "-p",
        # 上流パーサ(`redi news -p 1 create ...`)で指定された値を
        # サブパーサの default(None) で上書きしないよう SUPPRESS にする
        default=argparse.SUPPRESS,
        help=messages.arg_help_project_id,
    )
    n_create_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help=messages.arg_help_news_description,
    )
    n_create_parser.add_argument("--summary", "-s", help=messages.arg_help_news_summary)

    n_update_parser = n_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_news_update, parents=parents
    )
    n_update_parser.add_argument("news_id", help=messages.arg_help_news_update_id)
    n_update_parser.add_argument("--title", "-t", help=messages.arg_help_news_title_opt)
    n_update_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help=messages.arg_help_news_description,
    )
    n_update_parser.add_argument("--summary", "-s", help=messages.arg_help_news_summary)

    n_delete_parser = n_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_news_delete, parents=parents
    )
    n_delete_parser.add_argument("news_id", help=messages.arg_help_news_delete_id)
    n_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def handle_news(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.news_command)
    if cmd == "view":
        read_news(args.news_id, full=args.full)
        return
    if cmd == "create":
        project_id = args.project_id or default_project_id
        if not project_id:
            print(messages.project_id_required)
            sys.exit(1)
        description = args.description or open_editor()
        if not description:
            print(messages.canceled_empty_text)
            sys.exit(1)
        create_news(
            project_id=project_id,
            title=args.title,
            description=description,
            summary=args.summary,
        )
        return
    if cmd == "update":
        description = args.description
        if description == "":
            current = fetch_news(args.news_id)
            description = open_editor(current["description"])
            if not description:
                print(messages.canceled_empty_text)
                sys.exit(1)
        update_news(
            news_id=args.news_id,
            title=args.title,
            description=description,
            summary=args.summary,
        )
        return
    if cmd == "delete":
        if not args.yes:
            news = fetch_news(args.news_id)
            confirm_delete(
                messages.delete_target_news.format(id=news["id"], title=news["title"])
            )
        delete_news(args.news_id)
        return
    if cmd == "list" or cmd is None:
        project_id = args.project_id or default_project_id
        list_news(project_id=project_id, full=args.full)
