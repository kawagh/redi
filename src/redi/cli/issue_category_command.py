import argparse

from redi.cli._common import resolve_alias
from redi.config import default_project_id
from redi.api.issue_category import (
    create_issue_category,
    delete_issue_category,
    list_issue_categories,
    read_issue_category,
    update_issue_category,
)


def add_issue_category_parser(subparsers: argparse._SubParsersAction) -> None:
    ic_parser = subparsers.add_parser(
        "issue_category", help="イシューカテゴリ 一覧/作成/更新/削除"
    )
    ic_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    ic_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    ic_subparsers = ic_parser.add_subparsers(dest="issue_category_command")

    ic_view_parser = ic_subparsers.add_parser(
        "view", aliases=["v"], help="カテゴリ詳細"
    )
    ic_view_parser.add_argument("category_id", help="カテゴリID")
    ic_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )

    ic_create_parser = ic_subparsers.add_parser(
        "create", aliases=["c"], help="カテゴリ作成"
    )
    ic_create_parser.add_argument("name", help="カテゴリ名")
    ic_create_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    ic_create_parser.add_argument(
        "--assigned_to_id", type=int, help="デフォルト担当者のユーザーID"
    )

    ic_update_parser = ic_subparsers.add_parser(
        "update", aliases=["u"], help="カテゴリ更新"
    )
    ic_update_parser.add_argument("category_id", help="カテゴリID")
    ic_update_parser.add_argument("--name", "-n", help="カテゴリ名")
    ic_update_parser.add_argument(
        "--assigned_to_id", type=int, help="デフォルト担当者のユーザーID"
    )

    ic_delete_parser = ic_subparsers.add_parser(
        "delete", aliases=["d"], help="カテゴリ削除"
    )
    ic_delete_parser.add_argument("category_id", help="カテゴリID")
    ic_delete_parser.add_argument(
        "--reassign_to_id",
        type=int,
        help="削除に伴い既存チケットを再割り当てするカテゴリID",
    )


def handle_issue_category(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.issue_category_command)
    if cmd == "view":
        read_issue_category(args.category_id, full=args.full)
        return
    if cmd == "create":
        project_id = args.project_id or default_project_id
        if not project_id:
            print("project_idを指定するか、default_project_idを設定してください")
            exit(1)
        create_issue_category(
            project_id=project_id,
            name=args.name,
            assigned_to_id=args.assigned_to_id,
        )
        return
    if cmd == "update":
        update_issue_category(
            category_id=args.category_id,
            name=args.name,
            assigned_to_id=args.assigned_to_id,
        )
        return
    if cmd == "delete":
        delete_issue_category(
            category_id=args.category_id,
            reassign_to_id=args.reassign_to_id,
        )
        return
    project_id = args.project_id or default_project_id
    if not project_id:
        print("project_idを指定するか、default_project_idを設定してください")
        exit(1)
    list_issue_categories(project_id, full=args.full)
