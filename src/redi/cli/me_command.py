import argparse

from redi.api.me import read_my_account


def add_me_parser(subparsers: argparse._SubParsersAction) -> None:
    me_parser = subparsers.add_parser("me", help="自分のアカウント情報")
    me_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")


def handle_me(args: argparse.Namespace) -> None:
    read_my_account(full=args.full)
