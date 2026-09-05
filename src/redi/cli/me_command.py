"""`me` コマンドの表示整形。

取得・更新は `service.me_service` に任せ、ここでは print と sys.exit を担当する。
"""

import argparse
import json
import sys

import requests

from redi.api.exceptions import print_http_error_body
from redi.cli.alias import resolve_alias
from redi.cli.shared_options import add_format_options, wants_json
from redi.cli.user_format import format_user_detail
from redi.i18n import messages
from redi.output import eprint
from redi.service import me_service


def add_me_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    me_parser = subparsers.add_parser(
        "me", help=messages.arg_help_me_command, parents=parents
    )
    add_format_options(me_parser)
    me_subparsers = me_parser.add_subparsers(dest="me_command")

    me_update_parser = me_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_me_update, parents=parents
    )
    me_update_parser.add_argument(
        "--firstname", "-f", help=messages.arg_help_user_firstname
    )
    me_update_parser.add_argument(
        "--lastname", "-l", help=messages.arg_help_user_lastname
    )
    me_update_parser.add_argument("--mail", "-m", help=messages.arg_help_user_mail)


def view_my_account(full: bool = False) -> None:
    """自分のアカウントを標準出力に出す。

    既定の表示は `user view current` と同じ書式・同じ項目にするため、
    整形も取得元も `user view` と共有する。
    full=True では `/my/account.json` で取得した JSON をそのまま出す。
    """
    if full:
        print(json.dumps(me_service.read_my_account(), ensure_ascii=False))
        return
    print("\n".join(format_user_detail(me_service.read_my_user())))


def update_my_account(
    firstname: str | None = None,
    lastname: str | None = None,
    mail: str | None = None,
) -> None:
    """自分のアカウントを更新する。更新内容がなければ exit 1。"""
    if firstname is None and lastname is None and mail is None:
        eprint(messages.update_canceled_no_changes)
        sys.exit(1)
    try:
        me_service.update_my_account(firstname=firstname, lastname=lastname, mail=mail)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.account_update_failed)
        sys.exit(1)
    print(messages.account_updated)


def handle_me(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.me_command)
    if cmd == "update":
        update_my_account(
            firstname=args.firstname,
            lastname=args.lastname,
            mail=args.mail,
        )
        return
    view_my_account(full=wants_json(args))
