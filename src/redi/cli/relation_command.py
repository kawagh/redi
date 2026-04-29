import argparse

from redi.api.issue_relation import read_relation
from redi.cli._common import resolve_alias
from redi.i18n import messages


def add_relation_parser(subparsers: argparse._SubParsersAction) -> None:
    r_parser = subparsers.add_parser(
        "relation", help=messages.arg_help_relation_command
    )
    r_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    r_subparsers = r_parser.add_subparsers(dest="relation_command")
    r_parser.set_defaults(_print_help=r_parser.print_help)
    r_view_parser = r_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_relation_view
    )
    r_view_parser.add_argument("relation_id", help=messages.arg_help_relation_view_id)
    r_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def handle_relation(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.relation_command)
    if cmd == "view":
        read_relation(args.relation_id, full=args.full)
        return
    args._print_help()
