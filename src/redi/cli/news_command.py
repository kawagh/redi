import argparse
import sys

from redi import config
from redi.api.news import (
    News,
    create_news,
    delete_news,
    fetch_news,
    fetch_news_list,
    list_news,
    read_news,
    update_news,
)
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.editor import open_editor, shorten_to_oneline
from redi.cli.filter_parser import project_filter_parser
from redi.cli.interactive import prompt
from redi.cli.picker import inline_checkbox, inline_choice
from redi.cli.validator import RequiredValidator
from redi.i18n import messages


def _edit_description(initial_text: str = "") -> str:
    """エディタで説明を入力させ、入力内容を 1 行に畳んで表示する。

    エディタを閉じると入力内容が見えなくなるため表示する。
    空のまま閉じられた場合はキャンセルして終了する。
    """
    description = open_editor(initial_text)
    if not description:
        print(messages.canceled_empty_text)
        sys.exit(1)
    print(
        messages.prompt_field_value.format(
            name=messages.field_description,
            value=shorten_to_oneline(description),
        )
    )
    return description


def _interactive_select_news_id(
    project_id: str | None,
    prompt_message: str,
    selected_message: str | None = None,
) -> str:
    """ニュースを選ばせて id を返す。

    selected_message を渡すと選んだニュースを `{label}` に埋めて表示する。
    削除のように後段で対象を表示する場合は省略する。
    """
    news_list = fetch_news_list(project_id)
    if not news_list:
        print(messages.no_news_available)
        sys.exit(1)
    options: list[tuple[str, str]] = [
        (str(n["id"]), f"{n['id']} {n['title']}") for n in news_list
    ]
    labels = dict(options)
    try:
        news_id = inline_choice(prompt_message, options)
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)
    if selected_message is not None:
        print(selected_message.format(label=labels[news_id]))
    return news_id


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
    except (KeyboardInterrupt, EOFError):
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
        description = _edit_description(news["description"])
    return title, summary, description


def add_news_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    n_parser = subparsers.add_parser(
        "news",
        aliases=["n"],
        help=messages.arg_help_news_command,
        parents=[*parents, project_filter_parser()],
    )
    n_subparsers = n_parser.add_subparsers(dest="news_command")
    n_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_news_list,
        parents=[*parents, project_filter_parser(postfix=True)],
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
    n_create_parser.add_argument(
        "title", nargs="?", help=messages.arg_help_news_create_title
    )
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
    n_update_parser.add_argument(
        "news_id", nargs="?", help=messages.arg_help_news_update_id
    )
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
    n_delete_parser.add_argument(
        "news_id", nargs="?", help=messages.arg_help_news_delete_id
    )
    n_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def handle_news(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.news_command)
    if cmd == "view":
        read_news(args.news_id, full=args.full, web=args.web)
        return
    if cmd == "create":
        project_id = args.project_id or config.default_project_id
        if not project_id:
            print(messages.project_id_required)
            sys.exit(1)
        title = args.title
        summary = args.summary
        if title is None:
            try:
                title = prompt(
                    messages.prompt_title, validator=RequiredValidator()
                ).strip()
                if summary is None:
                    # 任意項目なので空のまま確定したら設定しない
                    summary = prompt(messages.prompt_summary).strip() or None
            except (KeyboardInterrupt, EOFError):
                print(messages.canceled)
                sys.exit(1)
        description = args.description or _edit_description()
        create_news(
            project_id=project_id,
            title=title,
            description=description,
            summary=summary,
        )
        return
    if cmd == "update":
        news_id = args.news_id or _interactive_select_news_id(
            args.project_id or config.default_project_id,
            messages.prompt_select_news_to_update,
            messages.update_target_news,
        )
        title = args.title
        summary = args.summary
        description = args.description
        if title is None and summary is None and description is None:
            # 更新項目が 1 つも指定されていないので対話で選ばせる
            title, summary, description = _interactive_fill_news_update(
                fetch_news(news_id)
            )
        elif description == "":
            description = _edit_description(fetch_news(news_id)["description"])
        update_news(
            news_id=news_id,
            title=title,
            description=description or None,
            summary=summary,
        )
        return
    if cmd == "delete":
        news_id = args.news_id or _interactive_select_news_id(
            args.project_id or config.default_project_id,
            messages.prompt_select_news_to_delete,
        )
        if not args.yes:
            news = fetch_news(news_id)
            confirm_delete(
                messages.delete_target_news.format(id=news["id"], title=news["title"])
            )
        delete_news(news_id)
        return
    if cmd == "list" or cmd is None:
        project_id = args.project_id or config.default_project_id
        list_news(project_id=project_id, full=args.full)
