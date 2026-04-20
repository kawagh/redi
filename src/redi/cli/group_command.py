import argparse

from redi.api.group import list_groups


def add_group_parser(subparsers: argparse._SubParsersAction) -> None:
    group_parser = subparsers.add_parser("group", help="グループ一覧")
    group_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def handle_group(args: argparse.Namespace) -> None:
    list_groups(full=args.full)
