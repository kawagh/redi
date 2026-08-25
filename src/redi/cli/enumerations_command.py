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
from redi.api.tracker import fetch_trackers
from redi.i18n import messages
from redi.output import eprint
from redi.service import query_service


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
    fetch: Callable[[bool], Sequence[Mapping[str, Any]] | None]
    # 応答をキャッシュするリソースにだけ --refresh を生やす
    cached: bool = True
    # fetch が None を返し得るリソースで、返ったときに表示する理由
    unavailable_message: str | None = None
    # `{id} {name}` では情報が落ちるリソースだけ整形を差し替える。
    # 一覧全体を受けるのは、行を組み立てる前に一括で引きたい情報があるため
    format_lines: Callable[[Sequence[Mapping[str, Any]]], list[str]] | None = None


def _format_query_lines(queries: Sequence[Mapping[str, Any]]) -> list[str]:
    """カスタムクエリを `{id} {name} [非公開] ({プロジェクト})` の 1 行で表示する。

    `/queries.json` はクエリのフィルタ内容を返さないため、素性の手がかりは
    名前と `is_public` / `project_id` しかない。共通整形はこのうち 2 つを
    捨ててしまうので、query だけ整形を差し替える。

    どちらも常に返るフィールドなので既定値は置かない (欠けたときに
    「公開」「全プロジェクト」と偽って表示するより落ちた方がよい)。

    クエリ名には空白が入り得るので、後ろに続く情報は括弧で括って name との
    境界が読めるようにする。
    """
    project_names = query_service.resolve_query_project_names(queries)
    lines = []
    for query in queries:
        parts = [f"{query['id']} {query['name']}"]
        if not query["is_public"]:
            parts.append(messages.query_list_private)
        project_id = query["project_id"]
        if project_id is None:
            parts.append(messages.query_list_all_projects)
        else:
            project_name = project_names.get(project_id)
            if project_name is None:
                parts.append(messages.query_list_unknown_project.format(id=project_id))
            else:
                parts.append(messages.query_list_project.format(name=project_name))
        lines.append(" ".join(parts))
    return lines


ENUMERATION_RESOURCES: tuple[EnumerationResource, ...] = (
    EnumerationResource(
        "tracker",
        "t",
        messages.arg_help_tracker_command,
        messages.arg_help_tracker_list,
        fetch_trackers,
    ),
    EnumerationResource(
        "issue_status",
        "is",
        messages.arg_help_issue_status_command,
        messages.arg_help_issue_status_list,
        fetch_issue_statuses,
    ),
    EnumerationResource(
        "issue_priority",
        "ip",
        messages.arg_help_issue_priority_command,
        messages.arg_help_issue_priority_list,
        fetch_issue_priorities,
    ),
    EnumerationResource(
        "time_entry_activity",
        "tea",
        messages.arg_help_time_entry_activity_command,
        messages.arg_help_time_entry_activity_list,
        fetch_time_entry_activities,
    ),
    EnumerationResource(
        "document_category",
        "dc",
        messages.arg_help_document_category_command,
        messages.arg_help_document_category_list,
        fetch_document_categories,
    ),
    EnumerationResource(
        "query",
        "q",
        messages.arg_help_query_command,
        messages.arg_help_query_list,
        # list_queries だけ refresh を取らないので合わせる
        lambda refresh: query_service.list_queries(),
        cached=False,
        format_lines=_format_query_lines,
    ),
    EnumerationResource(
        "custom_field",
        "cf",
        messages.arg_help_custom_field_command,
        messages.arg_help_custom_field_list,
        fetch_custom_fields,
        unavailable_message=messages.custom_field_admin_required,
    ),
)


def _print_enumeration(
    items: Iterable[Mapping[str, Any]], full: bool, resource: EnumerationResource
) -> None:
    """一覧専用リソースを 1 行ずつ表示する。

    既定は `{id} {name}` で、リソースが整形を持つ場合はそちらに任せる。
    """
    items = list(items)
    if full:
        print(json.dumps(items, ensure_ascii=False))
        return
    if resource.format_lines is not None:
        lines = resource.format_lines(items)
    else:
        lines = [f"{item['id']} {item['name']}" for item in items]
    for line in lines:
        print(line)


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
        eprint(resource.unavailable_message)
        sys.exit(1)
    _print_enumeration(items, args.full, resource)
