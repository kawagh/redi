import argparse
import json
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
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


@dataclass(frozen=True)
class EnumerationResource:
    """一覧しか持たないリソースの定義。

    parser 登録もハンドラもこの定義 1 件から組み立てるので、
    オプションを増やすときの変更箇所を 1 箇所に閉じ込められる。
    """

    name: str
    alias: str
    command_help: str
    list_help: str
    # 遅延束縛のため関数そのものではなく呼び出し式を保持する
    fetch: Callable[[bool], Sequence[Mapping[str, Any]] | None]
    # 応答をキャッシュするリソースにだけ --refresh を生やす
    cached: bool = True
    # fetch が None を返し得るリソースで、返ったときに表示する理由
    unavailable_message: str | None = None


ENUMERATION_RESOURCES: tuple[EnumerationResource, ...] = (
    EnumerationResource(
        "tracker",
        "t",
        messages.arg_help_tracker_command,
        messages.arg_help_tracker_list,
        lambda refresh: fetch_trackers(refresh=refresh),
    ),
    EnumerationResource(
        "issue_status",
        "is",
        messages.arg_help_issue_status_command,
        messages.arg_help_issue_status_list,
        lambda refresh: fetch_issue_statuses(refresh=refresh),
    ),
    EnumerationResource(
        "issue_priority",
        "ip",
        messages.arg_help_issue_priority_command,
        messages.arg_help_issue_priority_list,
        lambda refresh: fetch_issue_priorities(refresh=refresh),
    ),
    EnumerationResource(
        "time_entry_activity",
        "tea",
        messages.arg_help_time_entry_activity_command,
        messages.arg_help_time_entry_activity_list,
        lambda refresh: fetch_time_entry_activities(refresh=refresh),
    ),
    EnumerationResource(
        "document_category",
        "dc",
        messages.arg_help_document_category_command,
        messages.arg_help_document_category_list,
        lambda refresh: fetch_document_categories(refresh=refresh),
    ),
    EnumerationResource(
        "query",
        "q",
        messages.arg_help_query_command,
        messages.arg_help_query_list,
        lambda refresh: fetch_queries(),
        cached=False,
    ),
    EnumerationResource(
        "custom_field",
        "cf",
        messages.arg_help_custom_field_command,
        messages.arg_help_custom_field_list,
        lambda refresh: fetch_custom_fields(refresh=refresh),
        unavailable_message=messages.custom_field_admin_required,
    ),
)


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
    resource: EnumerationResource,
    parents: list[argparse.ArgumentParser],
) -> None:
    """一覧専用リソースに list (alias: l) サブコマンドを追加する

    引数無しの呼び出しと同じ挙動になるよう、handle 側では dest を参照しない。
    cached なリソースは応答をキャッシュするので --refresh も受け付ける。
    """
    subparsers = parser.add_subparsers(dest=f"{resource.name}_command")
    list_parser = subparsers.add_parser(
        "list", aliases=["l"], help=resource.list_help, parents=parents
    )
    list_parser.add_argument(
        "--full",
        action="store_true",
        # 未指定時に親パーサの --full を上書きしないようにする
        default=argparse.SUPPRESS,
        help=messages.arg_help_full_json,
    )
    if resource.cached:
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


def add_enumeration_parsers(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    """一覧専用リソースのサブコマンドをまとめて登録する。"""
    for resource in ENUMERATION_RESOURCES:
        parser = subparsers.add_parser(
            resource.name,
            aliases=[resource.alias],
            help=resource.command_help,
            parents=parents,
        )
        parser.add_argument(
            "--full", action="store_true", help=messages.arg_help_full_json
        )
        if resource.cached:
            _add_refresh_option(parser)
        _add_list_subparser(parser, resource, parents)


def find_enumeration_resource(command: str) -> EnumerationResource | None:
    """コマンド名またはエイリアスからリソース定義を引く。"""
    for resource in ENUMERATION_RESOURCES:
        if command in (resource.name, resource.alias):
            return resource
    return None


def handle_enumeration(resource: EnumerationResource, args: argparse.Namespace) -> None:
    # cached でないリソースには --refresh が無いので既定値で補う
    items = resource.fetch(getattr(args, "refresh", False))
    if items is None:
        print(resource.unavailable_message)
        sys.exit(1)
    _print_id_name_list(items, args.full)
