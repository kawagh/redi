import argparse

from redi.cli._common import resolve_alias
from redi.api.role import list_roles, read_role


def add_role_parser(subparsers: argparse._SubParsersAction) -> None:
    role_parser = subparsers.add_parser("role", help="list(l): 一覧, view(v): 詳細")
    role_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    role_subparsers = role_parser.add_subparsers(dest="role_command")
    role_subparsers.add_parser("list", aliases=["l"], help="ロール一覧")
    role_view_parser = role_subparsers.add_parser(
        "view", aliases=["v"], help="ロール詳細"
    )
    role_view_parser.add_argument("role_id", help="ロールID")
    role_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def handle_role(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.role_command)
    if cmd == "view":
        read_role(args.role_id, full=args.full)
    elif cmd == "list" or cmd is None:
        list_roles(full=args.full)
