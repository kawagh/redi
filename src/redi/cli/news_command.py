import argparse
import sys

from prompt_toolkit import prompt

from redi.api.news import (
    News,
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
from redi.cli.picker import inline_checkbox
from redi.config import default_project_id
from redi.i18n import messages


def _interactive_fill_news_update(news: News) -> tuple[str | None, str | None, str]:
    """更新する項目を選ばせて (title, summary, description) を返す。

    選ばれなかった項目は None(更新しない)。description は選ばれなければ空文字。
    issue update と同じく、更新項目が 1 つも指定されずに呼ばれたときに使う。
    """
    field_values: list[tuple[str, str]] = [
        ("title", messages.field_title),
        ("summary", messages.field_summary),
        ("description", messages.field_description),
    ]
    try:
        selected = inline_checkbox(
            messages.prompt_select_update_items,
            field_values,
            initial_value="description",
        )
    except KeyboardInterrupt:
        print(messages.canceled)
        sys.exit(1)
    if not selected:
        print(messages.canceled_no_items_selected)
        sys.exit(1)
    labels = dict(field_values)
    print(messages.update_items.format(items=", ".join(labels[v] for v in selected)))
    title: str | None = None
    summary: str | None = None
    description = ""
    try:
        if "title" in selected:
            title = prompt(messages.prompt_title, default=news["title"]).strip()
        if "summary" in selected:
            summary = prompt(
                messages.prompt_summary, default=news.get("summary") or ""
            ).strip()
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)
    if "description" in selected:
        description = open_editor(news["description"])
        if not description:
            print(messages.canceled_empty_text)
            sys.exit(1)
    return title, summary, description


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
    n_view_parser.add_argument(
        "--web", "-w", action="store_true", help=messages.arg_help_open_web
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
        read_news(args.news_id, full=args.full, web=args.web)
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
        title = args.title
        summary = args.summary
        description = args.description
        if title is None and summary is None and description is None:
            # 更新項目が 1 つも指定されていないので対話で選ばせる
            title, summary, description = _interactive_fill_news_update(
                fetch_news(args.news_id)
            )
        elif description == "":
            current = fetch_news(args.news_id)
            description = open_editor(current["description"])
            if not description:
                print(messages.canceled_empty_text)
                sys.exit(1)
        update_news(
            news_id=args.news_id,
            title=title,
            description=description or None,
            summary=summary,
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
