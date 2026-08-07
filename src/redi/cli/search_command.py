import argparse
from typing import cast

from redi.api.search import (
    SEARCH_ATTACHMENTS,
    SEARCH_SCOPES,
    SEARCH_TYPES,
    SearchType,
    search,
)
from redi.i18n import messages


def _parse_search_types(value: str) -> list[SearchType]:
    """カンマ区切りの検索種別を検証してリストに変換する。"""
    types = [t.strip() for t in value.split(",") if t.strip()]
    unknown = [t for t in types if t not in SEARCH_TYPES]
    if unknown:
        raise argparse.ArgumentTypeError(
            messages.error_invalid_search_type.format(
                values=",".join(unknown), choices=",".join(SEARCH_TYPES)
            )
        )
    return cast(list[SearchType], types)


def add_search_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    search_parser = subparsers.add_parser(
        "search", aliases=["s"], help=messages.arg_help_search_command, parents=parents
    )
    search_parser.add_argument("query", help=messages.arg_help_search_query)
    search_parser.add_argument("--limit", "-l", type=int, help=messages.arg_help_limit)
    search_parser.add_argument(
        "--offset", "-o", type=int, help=messages.arg_help_offset
    )
    search_parser.add_argument(
        "--scope", choices=SEARCH_SCOPES, help=messages.arg_help_search_scope
    )
    search_parser.add_argument(
        "--no_all_words",
        dest="all_words",
        action="store_false",
        default=None,
        help=messages.arg_help_search_no_all_words,
    )
    search_parser.add_argument(
        "--titles_only", action="store_true", help=messages.arg_help_search_titles_only
    )
    search_parser.add_argument(
        "--open_issues", action="store_true", help=messages.arg_help_search_open_issues
    )
    search_parser.add_argument(
        "--attachments",
        choices=SEARCH_ATTACHMENTS,
        help=messages.arg_help_search_attachments,
    )
    search_parser.add_argument(
        "--type",
        type=_parse_search_types,
        help=messages.arg_help_search_type.format(choices=",".join(SEARCH_TYPES)),
    )
    search_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def handle_search(args: argparse.Namespace) -> None:
    search(
        query=args.query,
        limit=args.limit,
        offset=args.offset,
        scope=args.scope,
        all_words=args.all_words,
        titles_only=args.titles_only,
        open_issues=args.open_issues,
        attachments=args.attachments,
        types=args.type,
        full=args.full,
    )
