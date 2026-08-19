import argparse
import json
import sys
from collections.abc import Iterable, Mapping
from typing import Any

from redi.api.custom_field import fetch_custom_fields
from redi.api.enumeration import (
    fetch_document_categories,
    fetch_issue_priorities,
    fetch_time_entry_activities,
)
from redi.api.issue_status import fetch_issue_statuses
from redi.api.query import fetch_queries
from redi.api.tracker import fetch_trackers
from redi.i18n import messages


def _print_id_name_list(items: Iterable[Mapping[str, Any]], full: bool) -> None:
    """一覧専用リソースを `{id} {name}` の 1 行で表示する。"""
    items = list(items)
    if full:
        print(json.dumps(items, ensure_ascii=False))
        return
    for item in items:
        print(f"{item['id']} {item['name']}")


def _add_list_subparser(
    parser: argparse.ArgumentParser,
    dest: str,
    help_: str,
    parents: list[argparse.ArgumentParser],
    *,
    cached: bool = False,
) -> None:
    """一覧専用リソースに list (alias: l) サブコマンドを追加する

    引数無しの呼び出しと同じ挙動になるよう、handle 側では dest を参照しない。
    cached=True のリソースは応答をキャッシュするので --refresh も受け付ける。
    """
    subparsers = parser.add_subparsers(dest=dest)
    list_parser = subparsers.add_parser(
        "list", aliases=["l"], help=help_, parents=parents
    )
    list_parser.add_argument(
        "--full",
        action="store_true",
        # 未指定時に親パーサの --full を上書きしないようにする
        default=argparse.SUPPRESS,
        help=messages.arg_help_full_json,
    )
    if cached:
        _add_refresh_option(list_parser, postfix=True)


def _add_refresh_option(
    parser: argparse.ArgumentParser, *, postfix: bool = False
) -> None:
    """キャッシュを持つリソースに --refresh を追加する。

    TTL が実質無期限なので、Redmine 側でトラッカーやカスタムフィールドを
    増やしてもこれを付けない限り古い値を返し続ける。
    """
    parser.add_argument(
        "--refresh",
        action="store_true",
        # 未指定の store_true が親パーサの True を False に戻すのを防ぐ
        default=argparse.SUPPRESS if postfix else False,
        help=messages.arg_help_refresh,
    )


def add_tracker_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    tracker_parser = subparsers.add_parser(
        "tracker",
        aliases=["t"],
        help=messages.arg_help_tracker_command,
        parents=parents,
    )
    tracker_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    _add_refresh_option(tracker_parser)
    _add_list_subparser(
        tracker_parser,
        "tracker_command",
        messages.arg_help_tracker_list,
        parents,
        cached=True,
    )


def handle_tracker(args: argparse.Namespace) -> None:
    _print_id_name_list(fetch_trackers(refresh=args.refresh), args.full)


def add_issue_status_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    issue_status_parser = subparsers.add_parser(
        "issue_status",
        aliases=["is"],
        help=messages.arg_help_issue_status_command,
        parents=parents,
    )
    issue_status_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    _add_refresh_option(issue_status_parser)
    _add_list_subparser(
        issue_status_parser,
        "issue_status_command",
        messages.arg_help_issue_status_list,
        parents,
        cached=True,
    )


def handle_issue_status(args: argparse.Namespace) -> None:
    _print_id_name_list(fetch_issue_statuses(refresh=args.refresh), args.full)


def add_issue_priority_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    ip_parser = subparsers.add_parser(
        "issue_priority",
        aliases=["ip"],
        help=messages.arg_help_issue_priority_command,
        parents=parents,
    )
    ip_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    _add_refresh_option(ip_parser)
    _add_list_subparser(
        ip_parser,
        "issue_priority_command",
        messages.arg_help_issue_priority_list,
        parents,
        cached=True,
    )


def handle_issue_priority(args: argparse.Namespace) -> None:
    _print_id_name_list(fetch_issue_priorities(refresh=args.refresh), args.full)


def add_time_entry_activity_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    tea_parser = subparsers.add_parser(
        "time_entry_activity",
        aliases=["tea"],
        help=messages.arg_help_time_entry_activity_command,
        parents=parents,
    )
    tea_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    _add_refresh_option(tea_parser)
    _add_list_subparser(
        tea_parser,
        "time_entry_activity_command",
        messages.arg_help_time_entry_activity_list,
        parents,
        cached=True,
    )


def handle_time_entry_activity(args: argparse.Namespace) -> None:
    _print_id_name_list(fetch_time_entry_activities(refresh=args.refresh), args.full)


def add_document_category_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    dc_parser = subparsers.add_parser(
        "document_category",
        aliases=["dc"],
        help=messages.arg_help_document_category_command,
        parents=parents,
    )
    dc_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    _add_refresh_option(dc_parser)
    _add_list_subparser(
        dc_parser,
        "document_category_command",
        messages.arg_help_document_category_list,
        parents,
        cached=True,
    )


def handle_document_category(args: argparse.Namespace) -> None:
    _print_id_name_list(fetch_document_categories(refresh=args.refresh), args.full)


def add_query_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    query_parser = subparsers.add_parser(
        "query", aliases=["q"], help=messages.arg_help_query_command, parents=parents
    )
    query_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    _add_list_subparser(
        query_parser, "query_command", messages.arg_help_query_list, parents
    )


def handle_query(args: argparse.Namespace) -> None:
    _print_id_name_list(fetch_queries(), args.full)


def add_custom_field_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    cf_parser = subparsers.add_parser(
        "custom_field",
        aliases=["cf"],
        help=messages.arg_help_custom_field_command,
        parents=parents,
    )
    cf_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    _add_refresh_option(cf_parser)
    _add_list_subparser(
        cf_parser,
        "custom_field_command",
        messages.arg_help_custom_field_list,
        parents,
        cached=True,
    )


def handle_custom_field(args: argparse.Namespace) -> None:
    custom_fields = fetch_custom_fields(refresh=args.refresh)
    if custom_fields is None:
        print(messages.custom_field_admin_required)
        sys.exit(1)
    _print_id_name_list(custom_fields, args.full)
