import argparse

from redi.cli._common import resolve_alias
from redi.api.group import (
    create_group,
    delete_group,
    list_groups,
    read_group,
    update_group,
)


def add_group_parser(subparsers: argparse._SubParsersAction) -> None:
    group_parser = subparsers.add_parser("group", help="グループ一覧/作成/更新")
    group_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    group_subparsers = group_parser.add_subparsers(dest="group_command")
    g_view_parser = group_subparsers.add_parser(
        "view", aliases=["v"], help="グループ詳細"
    )
    g_view_parser.add_argument("group_id", help="グループID")
    g_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    g_create_parser = group_subparsers.add_parser(
        "create", aliases=["c"], help="グループ作成（管理者権限が必要）"
    )
    g_create_parser.add_argument("name", help="グループ名")
    g_create_parser.add_argument(
        "--user_id",
        type=int,
        action="append",
        dest="user_ids",
        help="所属させるユーザーID（複数指定可）",
    )
    g_update_parser = group_subparsers.add_parser(
        "update", aliases=["u"], help="グループ更新（管理者権限が必要）"
    )
    g_update_parser.add_argument("group_id", help="グループID")
    g_update_parser.add_argument("--name", "-n", help="グループ名")
    g_update_parser.add_argument(
        "--user_id",
        type=int,
        action="append",
        dest="user_ids",
        help="所属ユーザーIDを指定（複数指定可、既存の所属ユーザーを置き換え）",
    )
    g_delete_parser = group_subparsers.add_parser(
        "delete", aliases=["d"], help="グループ削除（管理者権限が必要）"
    )
    g_delete_parser.add_argument("group_id", help="グループID")


def handle_group(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.group_command)
    if cmd == "view":
        read_group(args.group_id, full=args.full)
        return
    if cmd == "create":
        create_group(name=args.name, user_ids=args.user_ids)
        return
    if cmd == "update":
        update_group(
            group_id=args.group_id,
            name=args.name,
            user_ids=args.user_ids,
        )
        return
    if cmd == "delete":
        delete_group(args.group_id)
        return
    list_groups(full=args.full)
