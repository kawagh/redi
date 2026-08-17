"""`me` コマンドの表示整形。

取得・更新は `service.me_service` に任せ、ここでは print と sys.exit を担当する。
"""

import argparse
import json
import sys

import requests

from redi.api.exceptions import print_http_error_body
from redi.api.me import MyAccount
from redi.cli.alias import resolve_alias
from redi.i18n import messages
from redi.service import me_service


def add_me_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    me_parser = subparsers.add_parser(
        "me", help=messages.arg_help_me_command, parents=parents
    )
    me_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
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


def format_my_account_detail(account: MyAccount) -> list[str]:
    """自分のアカウントの詳細表示を行のリストに整形する。"""
    lines = [f"{account['id']} {account.get('login', '')}"]
    name = " ".join(filter(None, [account.get("firstname"), account.get("lastname")]))
    if name:
        lines.append(messages.label_name.format(value=name))
    if account.get("mail"):
        lines.append(messages.label_mail.format(value=account["mail"]))
    if "admin" in account:
        lines.append(messages.label_admin.format(value=account["admin"]))
    if account.get("created_on"):
        lines.append(messages.label_created_on.format(value=account["created_on"]))
    if account.get("last_login_on"):
        lines.append(
            messages.label_last_login_on.format(value=account["last_login_on"])
        )
    custom_fields = account.get("custom_fields") or []
    if custom_fields:
        lines.append(messages.label_custom_fields_header)
        for cf in custom_fields:
            lines.append(f"  {cf.get('name')}: {cf.get('value')}")
    return lines


def view_my_account(full: bool = False) -> None:
    """自分のアカウントを標準出力に出す。full=True では取得した JSON をそのまま出す。"""
    account = me_service.read_my_account()
    if full:
        print(json.dumps(account, ensure_ascii=False))
        return
    print("\n".join(format_my_account_detail(account)))


def update_my_account(
    firstname: str | None = None,
    lastname: str | None = None,
    mail: str | None = None,
) -> None:
    """自分のアカウントを更新する。更新内容がなければ exit 1。"""
    if firstname is None and lastname is None and mail is None:
        print(messages.update_canceled_no_changes)
        sys.exit(1)
    try:
        me_service.update_my_account(firstname=firstname, lastname=lastname, mail=mail)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.account_update_failed)
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
    view_my_account(full=args.full)
