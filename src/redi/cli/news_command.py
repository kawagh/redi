"""`news` サブコマンドの表示整形と対話。

取得や作成の手順は `service.news_service` に任せ、ここでは print と sys.exit を担当する。
"""

import argparse
import json
import sys
import webbrowser

import requests

from redi import config
from redi.api.exceptions import ProjectNotFoundException, print_http_error_body
from redi.api.news import News, NewsNotFoundException
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.editor import open_editor, shorten_to_oneline
from redi.cli.interactive import canceled_as_exit, prompt
from redi.cli.picker import inline_checkbox, inline_choice
from redi.cli.shared_options import project_option_parser
from redi.cli.validator import RequiredValidator
from redi.i18n import messages
from redi.output import eprint
from redi.service import news_service


def _fetch_news_list(project_id: str | None) -> list[News]:
    """ニュース一覧を取得する。プロジェクトが存在しなければ exit 1。"""
    try:
        return news_service.list_news(project_id)
    except ProjectNotFoundException:
        eprint(messages.project_not_found.format(id=project_id))
        sys.exit(1)


def _fetch_news(news_id: str) -> News:
    """ニュースを取得する。存在しなければ exit 1。"""
    try:
        return news_service.read_news(news_id)
    except NewsNotFoundException:
        eprint(messages.news_not_found.format(id=news_id))
        sys.exit(1)


def _list_news(project_id: str | None = None, full: bool = False) -> None:
    """ニュース一覧を1行ずつ出す。full=True では取得した JSON をそのまま出す。"""
    news_list = _fetch_news_list(project_id)
    if full:
        print(json.dumps(news_list, ensure_ascii=False))
        return
    for news in news_list:
        parts = [str(news["id"]), news["title"]]
        project = news["project"]["name"]
        if project:
            parts.append(f"[{project}]")
        author = news["author"]["name"]
        if author:
            parts.append(f"by {author}")
        if news["created_on"]:
            parts.append(news["created_on"])
        print(" ".join(parts))


def _view_news(news_id: str, full: bool = False, web: bool = False) -> None:
    """ニュースの詳細を標準出力に出す。存在しない場合は exit 1。"""
    if web:
        url = news_service.news_url(news_id)
        print(url)
        webbrowser.open(url)
        return
    news = _fetch_news(news_id)
    if full:
        print(json.dumps(news, ensure_ascii=False))
        return
    lines = [f"{news['id']} {news['title']}"]
    project = news["project"]
    lines.append(
        messages.label_project_field.format(id=project["id"], name=project["name"])
    )
    lines.append(messages.label_author.format(value=news["author"]["name"]))
    lines.append(messages.label_created_on.format(value=news["created_on"]))
    summary = news.get("summary")
    if summary:
        lines.append(messages.label_summary_field.format(value=summary))
    if news["description"]:
        lines.append("")
        lines.append(news["description"])
    attachments = news.get("attachments") or []
    if attachments:
        lines.append("")
        lines.append(messages.label_attachments_header)
        for a in attachments:
            lines.append(f"  {a['filename']} {a['content_url']}")
    comments = news.get("comments") or []
    if comments:
        lines.append("")
        lines.append(messages.label_news_comments_header)
        for c in comments:
            lines.append(f"  {c['id']} {c['author']['name']}")
            if c["content"]:
                lines.append(f"    {c['content'].strip()}")
    print("\n".join(lines))


def _create_news(
    project_id: str,
    title: str,
    description: str,
    summary: str | None = None,
) -> None:
    """ニュースを作成し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        url = news_service.create_news(
            project_id=project_id,
            title=title,
            description=description,
            summary=summary,
        )
    except ProjectNotFoundException:
        eprint(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.news_create_failed)
        sys.exit(1)
    print(messages.news_created.format(url=url))


def _update_news(
    news_id: str,
    title: str | None = None,
    description: str | None = None,
    summary: str | None = None,
) -> None:
    """ニュースを更新し、結果を標準出力に出す。失敗時は exit 1。"""
    if title is None and description is None and summary is None:
        print(messages.update_canceled)
        sys.exit()
    try:
        url = news_service.update_news(
            news_id,
            title=title,
            description=description,
            summary=summary,
        )
    except NewsNotFoundException:
        eprint(messages.news_not_found.format(id=news_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.news_update_failed)
        sys.exit(1)
    print(messages.news_updated.format(url=url))


def _delete_news(news_id: str) -> None:
    """ニュースを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        news_service.delete_news(news_id)
    except NewsNotFoundException:
        eprint(messages.news_not_found.format(id=news_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.news_delete_failed)
        sys.exit(1)
    print(messages.news_deleted.format(id=news_id))


def _edit_description(initial_text: str = "") -> str:
    """エディタで説明を入力させ、入力内容を 1 行に畳んで表示する。

    エディタを閉じると入力内容が見えなくなるため表示する。
    空のまま閉じられた場合はキャンセルして終了する。
    """
    description = open_editor(initial_text)
    if not description:
        eprint(messages.canceled_empty_text)
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
    news_list = _fetch_news_list(project_id)
    if not news_list:
        eprint(messages.no_news_available)
        sys.exit(1)
    options: list[tuple[str, str]] = [
        (str(n["id"]), f"{n['id']} {n['title']}") for n in news_list
    ]
    labels = dict(options)
    with canceled_as_exit():
        news_id = inline_choice(prompt_message, options)
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
    with canceled_as_exit():
        selected = inline_checkbox(
            messages.prompt_select_update_items,
            field_values,
            initial_value="description",
        )
    if not selected:
        eprint(messages.canceled_no_items_selected)
        sys.exit(1)
    labels = dict(field_values)
    print(messages.update_items.format(items=", ".join(labels[v] for v in selected)))
    title: str | None = None
    summary: str | None = None
    description = ""
    with canceled_as_exit():
        if "title" in selected:
            title = prompt(messages.prompt_title, default=news["title"]).strip()
        if "summary" in selected:
            summary = prompt(
                messages.prompt_summary, default=news.get("summary") or ""
            ).strip()
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
        parents=[*parents, project_option_parser()],
    )
    n_subparsers = n_parser.add_subparsers(dest="news_command")
    n_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_news_list,
        parents=[*parents, project_option_parser(postfix=True)],
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
        _view_news(args.news_id, full=args.full, web=args.web)
        return
    if cmd == "create":
        project_id = args.project_id or config.default_project_id
        if not project_id:
            eprint(messages.project_id_required)
            sys.exit(1)
        title = args.title
        summary = args.summary
        if title is None:
            with canceled_as_exit():
                title = prompt(
                    messages.prompt_title, validator=RequiredValidator()
                ).strip()
                if summary is None:
                    # 任意項目なので空のまま確定したら設定しない
                    summary = prompt(messages.prompt_summary).strip() or None
        description = args.description or _edit_description()
        _create_news(
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
                _fetch_news(news_id)
            )
        elif description == "":
            description = _edit_description(_fetch_news(news_id)["description"])
        _update_news(
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
            news = _fetch_news(news_id)
            confirm_delete(
                messages.delete_target_news.format(id=news["id"], title=news["title"])
            )
        _delete_news(news_id)
        return
    if cmd == "list" or cmd is None:
        project_id = args.project_id or config.default_project_id
        _list_news(project_id=project_id, full=args.full)
