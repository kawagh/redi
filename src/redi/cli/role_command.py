import argparse

from redi.api.role import list_roles, read_role
from redi.cli.alias import resolve_alias
from redi.cli.shared_options import full_option_parser
from redi.i18n import messages


def add_role_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    role_parser = subparsers.add_parser(
        "role",
        aliases=["r"],
        help=messages.arg_help_role_command,
        parents=[*parents, full_option_parser()],
    )
    role_subparsers = role_parser.add_subparsers(dest="role_command")
    role_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_role_list,
        parents=[*parents, full_option_parser(postfix=True)],
    )
    role_view_parser = role_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_role_view, parents=parents
    )
    role_view_parser.add_argument("role_id", help=messages.arg_help_role_view_id)
    role_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def handle_role(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.role_command)
    if cmd == "view":
        read_role(args.role_id, full=args.full)
    elif cmd == "list" or cmd is None:
        list_roles(full=args.full)
