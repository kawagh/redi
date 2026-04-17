import argparse

from redi.api.search import search


def add_search_parser(subparsers: argparse._SubParsersAction) -> None:
    search_parser = subparsers.add_parser("search", help="検索")
    search_parser.add_argument("query", help="検索クエリ")
    search_parser.add_argument("--limit", "-l", type=int, help="取得件数")
    search_parser.add_argument("--offset", "-o", type=int, help="オフセット")
    search_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def handle_search(args: argparse.Namespace) -> None:
    search(
        query=args.query,
        limit=args.limit,
        offset=args.offset,
        full=args.full,
    )
