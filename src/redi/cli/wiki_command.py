import argparse
import json
import sys
import webbrowser

import requests
from prompt_toolkit.validation import ValidationError, Validator

from redi import config
from redi.api.exceptions import print_http_error_body
from redi.api.wiki import (
    WikiPage,
    WikiPageNotFoundException,
    normalize_title,
)
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.editor import open_editor
from redi.cli.interactive import prompt
from redi.cli.picker import inline_choice
from redi.cli.shared_options import add_full_argument, project_option_parser
from redi.i18n import messages
from redi.service import wiki_service


def _prompt_wiki_comments() -> str:
    """commentsを対話的に入力してもらう。空文字は省略扱い。"""
    try:
        return prompt(messages.prompt_wiki_comments).strip()
    except (KeyboardInterrupt, EOFError):
        print(messages.canceled)
        sys.exit(1)


def _delete_page(project_id: str, page_title: str) -> None:
    """Wiki ページを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        wiki_service.delete_page(project_id, page_title)
    except WikiPageNotFoundException:
        print(messages.wiki_page_not_found.format(title=page_title))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.wiki_page_delete_failed)
        sys.exit(1)
    print(messages.wiki_page_deleted.format(title=page_title))


def _list_pages(project_id: str, full: bool = False) -> None:
    """Wiki ページ一覧をツリー表示する。full=True では取得した JSON をそのまま出す。"""
    pages = wiki_service.list_pages(project_id)
    if full:
        print(json.dumps(pages, ensure_ascii=False))
        return
    for page, tree_prefix in wiki_service.flatten_wiki_tree(pages):
        title = page["title"]
        print(f"{tree_prefix}[{title}]({wiki_service.page_url(project_id, title)})")


def _view_page(
    project_id: str,
    page_title: str,
    full: bool = False,
    web: bool = False,
    version: int | None = None,
) -> None:
    """Wiki ページの本文を標準出力に出す。存在しない場合は exit 1。"""
    if web:
        url = wiki_service.page_url(project_id, page_title, version=version)
        print(url)
        webbrowser.open(url)
        return
    page = wiki_service.read_page(project_id, page_title, version=version, full=full)
    if page is None:
        if version is not None:
            print(
                messages.wiki_page_with_version_not_found.format(
                    title=page_title, version=version
                )
            )
        else:
            print(messages.wiki_page_not_found.format(title=page_title))
        sys.exit(1)
    if full:
        print(json.dumps(page, ensure_ascii=False, indent=2))
    else:
        print(page.get("text", ""))


def _create_page(
    project_id: str,
    page_title: str,
    text: str,
    parent_title: str | None = None,
    comments: str = "",
) -> None:
    """Wiki ページを作成し、結果を標準出力に出す。親ページが無い場合は exit 1。"""
    try:
        result = wiki_service.create_page(
            project_id,
            page_title,
            text,
            parent_title=parent_title,
            comments=comments,
        )
    except wiki_service.ParentPageNotFoundException as e:
        print(messages.parent_page_not_found.format(title=e.title))
        sys.exit(1)
    url = wiki_service.page_url(project_id, result.title)
    if result.created:
        print(messages.wiki_page_created.format(url=url))
    else:
        print(messages.wiki_page_updated.format(url=url))


def _update_page(
    project_id: str,
    page_title: str,
    text: str,
    version: int | None = None,
    comments: str = "",
) -> None:
    """Wiki ページを更新し、結果を標準出力に出す。"""
    wiki_service.update_page(
        project_id, page_title, text, version=version, comments=comments
    )
    print(
        messages.wiki_page_updated.format(
            url=wiki_service.page_url(project_id, page_title)
        )
    )


def build_wiki_tree_choices(pages: list[WikiPage]) -> list[tuple[str, str]]:
    children_map = wiki_service.build_children_map(pages)
    options: list[tuple[str, str]] = []

    def walk(parent: str | None, depth: int) -> None:
        for title in children_map.get(parent, []):
            options.append((title, "  " * depth + title))
            walk(title, depth + 1)

    walk(None, 0)
    return options


def add_wiki_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    w_parser = subparsers.add_parser(
        "wiki",
        aliases=["w"],
        help=messages.arg_help_wiki_command,
        parents=[*parents, project_option_parser()],
    )
    w_subparsers = w_parser.add_subparsers(dest="wiki_command")
    w_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_wiki_list,
        parents=[*parents, project_option_parser(postfix=True)],
    )
    w_view_parser = w_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_wiki_view, parents=parents
    )
    w_view_parser.add_argument("page_title", help=messages.arg_help_wiki_page_title)
    add_full_argument(w_view_parser, postfix=True)
    w_view_parser.add_argument(
        "--web", "-w", action="store_true", help=messages.arg_help_open_web
    )
    w_view_parser.add_argument(
        "--version", type=int, help=messages.arg_help_wiki_version
    )
    w_create_parser = w_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_wiki_create, parents=parents
    )
    w_create_parser.add_argument(
        "page_title", nargs="?", help=messages.arg_help_wiki_create_title
    )
    w_create_parser.add_argument(
        "--parent_title", help=messages.arg_help_wiki_parent_title
    )
    w_create_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help=messages.arg_help_wiki_description,
    )
    w_create_parser.add_argument(
        "--comments",
        default="",
        help=messages.arg_help_wiki_comments,
    )
    w_delete_parser = w_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_wiki_delete, parents=parents
    )
    w_delete_parser.add_argument("page_title", help=messages.arg_help_wiki_page_title)
    w_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )
    w_update_parser = w_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_wiki_update, parents=parents
    )
    w_update_parser.add_argument(
        "page_title", nargs="?", help=messages.arg_help_wiki_update_title
    )
    w_update_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help=messages.arg_help_wiki_description,
    )
    w_update_parser.add_argument(
        "--comments",
        default="",
        help=messages.arg_help_wiki_comments,
    )


def handle_wiki(args: argparse.Namespace) -> None:
    project_id = args.project_id or config.wiki_project_id or config.default_project_id
    if not project_id:
        print(messages.wiki_project_id_required)
        sys.exit(1)
    cmd = resolve_alias(args.wiki_command)
    if cmd == "view":
        _view_page(
            project_id,
            args.page_title,
            full=args.full,
            web=args.web,
            version=args.version,
        )
    elif cmd == "create":
        page_title = args.page_title
        parent_title = args.parent_title
        if page_title is None:
            pages = wiki_service.list_pages(project_id)
            existing_titles = {normalize_title(p["title"]) for p in pages}

            class _PageTitleValidator(Validator):
                def validate(self, document) -> None:
                    stripped = document.text.strip()
                    if not stripped:
                        raise ValidationError(
                            message=messages.error_page_title_required
                        )
                    if normalize_title(stripped) in existing_titles:
                        raise ValidationError(
                            message=messages.error_page_title_duplicate
                        )

            try:
                page_title = prompt(
                    messages.prompt_page_title, validator=_PageTitleValidator()
                ).strip()
            except (KeyboardInterrupt, EOFError):
                print(messages.canceled)
                sys.exit(1)
            if not page_title:
                print(messages.canceled_empty_title)
                sys.exit(1)
            if parent_title is None:
                parent_options = build_wiki_tree_choices(pages)
                if parent_options:
                    parent_labels = dict(parent_options)
                    try:
                        parent_title = inline_choice(
                            messages.prompt_parent_page, parent_options
                        )
                    except (KeyboardInterrupt, EOFError):
                        print(messages.canceled)
                        sys.exit(1)
                    print(
                        messages.parent_page_label.format(
                            label=parent_labels[parent_title].strip()
                        )
                    )
        if args.description and args.description != "":
            text = args.description
            comments = args.comments
        else:
            text = open_editor()
            comments = args.comments or _prompt_wiki_comments()
        if text:
            page_title = normalize_title(page_title)
            if parent_title:
                parent_title = normalize_title(parent_title)
            _create_page(
                project_id,
                page_title,
                text,
                parent_title=parent_title,
                comments=comments,
            )
        else:
            print(messages.canceled_empty_text)
    elif cmd == "delete":
        title = normalize_title(args.page_title)
        if not args.yes:
            page = wiki_service.read_page(project_id, title)
            if page is None:
                print(messages.wiki_page_not_found.format(title=title))
                sys.exit(1)
            confirm_delete(
                messages.delete_target_wiki_page.format(title=page.get("title", title))
            )
        _delete_page(project_id, title)
    elif cmd == "update":
        page_title = args.page_title
        if page_title is None:
            pages = wiki_service.list_pages(project_id)
            if not pages:
                print(messages.wiki_page_does_not_exist)
                sys.exit(1)
            page_options = build_wiki_tree_choices(pages)
            page_labels = dict(page_options)
            try:
                page_title = inline_choice(messages.prompt_edit_page, page_options)
            except (KeyboardInterrupt, EOFError):
                print(messages.canceled)
                sys.exit(1)
            print(
                messages.edit_target_page.format(label=page_labels[page_title].strip())
            )
        version: int | None = None
        if args.description and args.description != "":
            text = args.description
            comments = args.comments
        else:
            current = wiki_service.read_page(project_id, page_title)
            if current is None:
                print(messages.wiki_page_not_found.format(title=page_title))
                sys.exit(1)
            version = current.get("version")
            text = open_editor(current.get("text") or "")
            comments = args.comments or _prompt_wiki_comments()
        if text:
            _update_page(
                project_id,
                page_title,
                text,
                version=version,
                comments=comments,
            )
        else:
            print(messages.canceled_empty_text)
    elif cmd == "list" or cmd is None:
        _list_pages(project_id, full=args.full)
