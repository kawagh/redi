import argparse


def add_tracker_parser(subparsers: argparse._SubParsersAction) -> None:
    tracker_parser = subparsers.add_parser("tracker", help="トラッカー一覧")
    tracker_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def add_issue_status_parser(subparsers: argparse._SubParsersAction) -> None:
    issue_status_parser = subparsers.add_parser("issue_status", help="ステータス一覧")
    issue_status_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def add_issue_priority_parser(subparsers: argparse._SubParsersAction) -> None:
    ip_parser = subparsers.add_parser("issue_priority", help="優先度一覧")
    ip_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")


def add_time_entry_activity_parser(subparsers: argparse._SubParsersAction) -> None:
    tea_parser = subparsers.add_parser("time_entry_activity", help="作業分類一覧")
    tea_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def add_document_category_parser(subparsers: argparse._SubParsersAction) -> None:
    dc_parser = subparsers.add_parser("document_category", help="文書カテゴリ一覧")
    dc_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")


def add_query_parser(subparsers: argparse._SubParsersAction) -> None:
    query_parser = subparsers.add_parser("query", help="カスタムクエリ一覧")
    query_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )


def add_custom_field_parser(subparsers: argparse._SubParsersAction) -> None:
    cf_parser = subparsers.add_parser("custom_field", help="カスタムフィールド一覧")
    cf_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
