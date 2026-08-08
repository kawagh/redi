import argparse

from redi.api.me import read_my_account, update_my_account
from redi.cli.alias import resolve_alias
from redi.i18n import messages


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
