import argparse

from redi.cli._common import resolve_alias
from redi.api.me import read_my_account, update_my_account


def add_me_parser(subparsers: argparse._SubParsersAction) -> None:
    me_parser = subparsers.add_parser("me", help="自分のアカウント情報 詳細/更新")
    me_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    me_subparsers = me_parser.add_subparsers(dest="me_command")

    me_update_parser = me_subparsers.add_parser(
        "update", aliases=["u"], help="自分のアカウント情報を更新"
    )
    me_update_parser.add_argument("--firstname", "-f", help="名")
    me_update_parser.add_argument("--lastname", "-l", help="姓")
    me_update_parser.add_argument("--mail", "-m", help="メールアドレス")


def handle_me(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.me_command)
    if cmd == "update":
        update_my_account(
            firstname=args.firstname,
            lastname=args.lastname,
            mail=args.mail,
        )
        return
    read_my_account(full=args.full)
