import argparse

from redi.api.search import search
from redi.i18n import messages


def add_search_parser(subparsers: argparse._SubParsersAction) -> None:
    search_parser = subparsers.add_parser(
        "search", help=messages.arg_help_search_command
    )
    search_parser.add_argument("query", help=messages.arg_help_search_query)
    search_parser.add_argument("--limit", "-l", type=int, help=messages.arg_help_limit)
    search_parser.add_argument(
        "--offset", "-o", type=int, help=messages.arg_help_offset
    )
    search_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def handle_search(args: argparse.Namespace) -> None:
    search(
        query=args.query,
        limit=args.limit,
        offset=args.offset,
        full=args.full,
    )
