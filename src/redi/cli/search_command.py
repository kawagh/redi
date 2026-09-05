import argparse
import json
import sys
from typing import cast

from redi.api.search import (
    SEARCH_ATTACHMENTS,
    SEARCH_SCOPES,
    SEARCH_TYPES,
    SearchScope,
    SearchType,
    search,
)
from redi.cli.shared_options import add_format_options, wants_json
from redi.i18n import messages
from redi.output import eprint


def _validate_scope(scope: SearchScope | None, project_id: str | None) -> None:
    """--scope と --project_id の組み合わせでエラーが返らないものをエラーにする

    - subprojects は project_id がないと成立しないのでproject_idを求める
    - project_id の指定がある場合は他のスコープの指定を受け付けないようにする
    """
    if scope is None:
        return
    if scope == "subprojects":
        if project_id is None:
            eprint(messages.error_search_scope_requires_project.format(scope=scope))
            sys.exit(1)
        return
    if project_id is not None:
        eprint(messages.error_search_scope_conflicts_project.format(scope=scope))
        sys.exit(1)


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
        "--project_id", "-p", help=messages.arg_help_search_project_id
    )
    search_parser.add_argument(
        "--scope", choices=SEARCH_SCOPES, help=messages.arg_help_search_scope
    )
    search_parser.add_argument(
        "--no_all_words",
        dest="all_words",
        action="store_false",
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
    add_format_options(search_parser)


def handle_search(args: argparse.Namespace) -> None:
    _validate_scope(args.scope, args.project_id)
    data = search(
        query=args.query,
        limit=args.limit,
        offset=args.offset,
        project_id=args.project_id,
        scope=args.scope,
        all_words=args.all_words,
        titles_only=args.titles_only,
        open_issues=args.open_issues,
        attachments=args.attachments,
        types=args.type,
    )
    if wants_json(args):
        print(json.dumps(data, ensure_ascii=False))
        return
    results = data.get("results", [])
    if not results:
        print(messages.no_search_results)
        return
    for r in results:
        print(f"[{r.get('type', '')}] {r.get('title', '')} {r.get('url', '')}")
