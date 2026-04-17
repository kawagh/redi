import argparse

import questionary

from redi.cli._common import open_editor, resolve_alias
from redi.config import default_project_id, wiki_project_id
from redi.api.wiki import (
    build_children_map,
    create_wiki,
    fetch_wiki,
    fetch_wikis,
    list_wikis,
    normalize_title,
    read_wiki,
    update_wiki,
)


def build_wiki_tree_choices(pages: list[dict]) -> list[questionary.Choice]:
    children_map = build_children_map(pages)
    choices: list[questionary.Choice] = []

    def walk(parent: str | None, depth: int) -> None:
        for title in children_map.get(parent, []):
            choices.append(questionary.Choice("  " * depth + title, value=title))
            walk(title, depth + 1)

    walk(None, 0)
    return choices


def add_wiki_parser(subparsers: argparse._SubParsersAction) -> None:
    w_parser = subparsers.add_parser("wiki", aliases=["w"], help="Wiki一覧/詳細/作成")
    w_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    w_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    w_subparsers = w_parser.add_subparsers(dest="wiki_command")
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
        print(
            "project_idを指定するか、wiki_project_idまたはdefault_project_idを設定してください"
        )
        exit(1)
    cmd = resolve_alias(args.wiki_command)
    if cmd == "view":
        read_wiki(project_id, args.page_title, full=args.full, web=args.web)
    elif cmd == "create":
        page_title = args.page_title
        parent_title = args.parent_title
        if page_title is None:
            pages = fetch_wikis(project_id)
            existing_titles = {normalize_title(p["title"]) for p in pages}

            def validate_page_title(value: str) -> bool | str:
                stripped = value.strip()
                if not stripped:
                    return "ページタイトルを入力してください"
                if normalize_title(stripped) in existing_titles:
                    return "既存のページタイトルと重複しています"
                return True

            page_title = questionary.text(
                "ページタイトル",
                validate=validate_page_title,
            ).ask(kbi_msg="")
            if not page_title:
                print("ページタイトルが空のためキャンセルしました")
                exit(1)
            if parent_title is None:
                parent_title = questionary.select(
                    "親ページ",
                    choices=build_wiki_tree_choices(pages),
                ).ask(kbi_msg="")
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
            print("テキストが空のためキャンセルしました")
    elif cmd == "update":
        page_title = args.page_title
        if page_title is None:
            pages = fetch_wikis(project_id)
            if not pages:
                print("Wikiページが存在しません")
                exit(1)
            page_title = questionary.select(
                "編集するページ",
                choices=build_wiki_tree_choices(pages),
            ).ask(kbi_msg="")
            if not page_title:
                print("キャンセルしました")
                exit(1)
        if args.description and args.description != "":
            text = args.description
        else:
            current = fetch_wiki(project_id, page_title)
            text = open_editor(current.get("text") or "")
        if text:
            update_wiki(project_id, page_title, text)
        else:
            print("テキストが空のためキャンセルしました")
    else:
        list_wikis(project_id, full=args.full)
