import argparse

from prompt_toolkit import prompt
from prompt_toolkit.validation import ValidationError, Validator

from redi.cli._common import confirm_delete, inline_choice, open_editor, resolve_alias
from redi.config import default_project_id, wiki_project_id
from redi.i18n import messages
from redi.api.wiki import (
    build_children_map,
    create_wiki,
    delete_wiki,
    fetch_wiki,
    fetch_wikis,
    list_wikis,
    normalize_title,
    read_wiki,
    update_wiki,
)


def build_wiki_tree_choices(pages: list[dict]) -> list[tuple[str, str]]:
    children_map = build_children_map(pages)
    options: list[tuple[str, str]] = []

    def walk(parent: str | None, depth: int) -> None:
        for title in children_map.get(parent, []):
            options.append((title, "  " * depth + title))
            walk(title, depth + 1)

    walk(None, 0)
    return options


def add_wiki_parser(subparsers: argparse._SubParsersAction) -> None:
    w_parser = subparsers.add_parser(
        "wiki",
        aliases=["w"],
        help="list(l): 一覧, view(v): 詳細, create(c): 作成, update(u): 更新, delete(d): 削除",
    )
    w_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    w_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    w_subparsers = w_parser.add_subparsers(dest="wiki_command")
    w_subparsers.add_parser("list", aliases=["l"], help="Wikiページ一覧")
    w_view_parser = w_subparsers.add_parser(
        "view", aliases=["v"], help="Wikiページ詳細"
    )
    w_view_parser.add_argument("page_title", help="Wikiページタイトル")
    w_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    w_view_parser.add_argument(
        "--web", "-w", action="store_true", help="ブラウザでRedmineのページを開く"
    )
    w_view_parser.add_argument(
        "--version", type=int, help="特定バージョンのページを取得"
    )
    w_create_parser = w_subparsers.add_parser(
        "create", aliases=["c"], help="Wikiページ作成"
    )
    w_create_parser.add_argument(
        "page_title", nargs="?", help="Wikiページタイトル（省略で対話的に入力）"
    )
    w_create_parser.add_argument("--parent_title", help="親ページタイトル")
    w_create_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help="説明（値省略でエディタ起動）",
    )
    w_delete_parser = w_subparsers.add_parser(
        "delete", aliases=["d"], help="Wikiページ削除"
    )
    w_delete_parser.add_argument("page_title", help="Wikiページタイトル")
    w_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help="確認プロンプトをスキップ"
    )
    w_update_parser = w_subparsers.add_parser(
        "update", aliases=["u"], help="Wikiページ更新"
    )
    w_update_parser.add_argument(
        "page_title", nargs="?", help="Wikiページタイトル（省略で対話的に選択）"
    )
    w_update_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help="説明（値省略でエディタ起動）",
    )


def handle_wiki(args: argparse.Namespace) -> None:
    project_id = args.project_id or wiki_project_id or default_project_id
    if not project_id:
        print(messages.wiki_project_id_required)
        exit(1)
    cmd = resolve_alias(args.wiki_command)
    if cmd == "view":
        read_wiki(
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
            pages = fetch_wikis(project_id)
            existing_titles = {normalize_title(p["title"]) for p in pages}

            class _PageTitleValidator(Validator):
                def validate(self, document) -> None:
                    stripped = document.text.strip()
                    if not stripped:
                        raise ValidationError(
                            message="ページタイトルを入力してください"
                        )
                    if normalize_title(stripped) in existing_titles:
                        raise ValidationError(
                            message="既存のページタイトルと重複しています"
                        )

            try:
                page_title = prompt(
                    "ページタイトル: ", validator=_PageTitleValidator()
                ).strip()
            except (KeyboardInterrupt, EOFError):
                print(messages.canceled)
                exit(1)
            if not page_title:
                print(messages.canceled_empty_title)
                exit(1)
            if parent_title is None:
                parent_options = build_wiki_tree_choices(pages)
                if parent_options:
                    parent_labels = dict(parent_options)
                    try:
                        parent_title = inline_choice("親ページ", parent_options)
                    except KeyboardInterrupt:
                        print(messages.canceled)
                        exit(1)
                    print(
                        messages.parent_page_label.format(
                            label=parent_labels[parent_title].strip()
                        )
                    )
        if args.description and args.description != "":
            text = args.description
        else:
            text = open_editor()
        if text:
            page_title = normalize_title(page_title)
            if parent_title:
                parent_title = normalize_title(parent_title)
            create_wiki(project_id, page_title, text, parent_title=parent_title)
        else:
            print(messages.canceled_empty_text)
    elif cmd == "delete":
        title = normalize_title(args.page_title)
        if not args.yes:
            page = fetch_wiki(project_id, title)
            if page is None:
                print(messages.wiki_page_not_found.format(title=title))
                exit(1)
            confirm_delete(f"削除するWikiページ: {page.get('title', title)}")
        delete_wiki(project_id, title)
    elif cmd == "update":
        page_title = args.page_title
        if page_title is None:
            pages = fetch_wikis(project_id)
            if not pages:
                print(messages.wiki_page_does_not_exist)
                exit(1)
            page_options = build_wiki_tree_choices(pages)
            page_labels = dict(page_options)
            try:
                page_title = inline_choice("編集するページ", page_options)
            except KeyboardInterrupt:
                print(messages.canceled)
                exit(1)
            print(
                messages.edit_target_page.format(label=page_labels[page_title].strip())
            )
        if args.description and args.description != "":
            text = args.description
        else:
            current = fetch_wiki(project_id, page_title)
            if current is None:
                print(messages.wiki_page_not_found.format(title=page_title))
                exit(1)
            text = open_editor(current.get("text") or "")
        if text:
            update_wiki(project_id, page_title, text)
        else:
            print(messages.canceled_empty_text)
    elif cmd == "list" or cmd is None:
        list_wikis(project_id, full=args.full)
