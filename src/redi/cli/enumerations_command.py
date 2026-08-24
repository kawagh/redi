import argparse
import json
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from redi.api.custom_field import (
    CustomField,
    fetch_custom_fields,
    find_custom_field,
)
from redi.api.enumeration import (
    fetch_document_categories,
    fetch_issue_priorities,
    fetch_time_entry_activities,
)
from redi.api.issue_status import fetch_issue_statuses
from redi.api.tracker import fetch_trackers
from redi.cli.alias import resolve_alias
from redi.i18n import messages
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
    # list 以外のサブコマンドを持つリソースだけが使う拡張点。
    # add_subcommands は list と同じ subparsers に追加登録し、
    # handle_subcommand は自分が扱えたときに True を返す。
    add_subcommands: (
        Callable[[argparse._SubParsersAction, list[argparse.ArgumentParser]], None]
        | None
    ) = None
    handle_subcommand: (
        Callable[[Sequence[Mapping[str, Any]], argparse.Namespace], bool] | None
    ) = None


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


# ---- custom_field だけが持つ view サブコマンド ----


def _add_custom_field_view_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    """custom_field に view <id> を追加する。"""
    view_parser = subparsers.add_parser(
        "view",
        aliases=["v"],
        help=messages.arg_help_custom_field_view,
        parents=parents,
    )
    view_parser.add_argument(
        "custom_field_id", help=messages.arg_help_custom_field_view_id
    )
    view_parser.add_argument(
        "--full",
        action="store_true",
        # 未指定時に親パーサの --full を上書きしないようにする
        default=argparse.SUPPRESS,
        help=messages.arg_help_full_json,
    )
    _add_refresh_option(view_parser, postfix=True)


def _format_bool(value: bool) -> str:
    return messages.label_bool_true if value else messages.label_bool_false


def _format_possible_value(possible_value: Mapping[str, Any]) -> str:
    """possible_values の 1 件を表示用の文字列にする。

    enumeration 形式は value が id・label が表示名なので両方出す。
    list 形式は value と label が同じ値なので value だけ出す。
    """
    value = str(possible_value.get("value", ""))
    label = str(possible_value.get("label", ""))
    if label and label != value:
        return f"{value} {label}"
    return value


def _print_custom_field(custom_field: CustomField, full: bool) -> None:
    """カスタムフィールド 1 件の詳細を表示する。"""
    if full:
        print(json.dumps(custom_field, ensure_ascii=False))
        return
    lines = [f"{custom_field['id']} {custom_field['name']}"]
    if custom_field.get("description"):
        lines.append(
            messages.label_description_field.format(value=custom_field["description"])
        )
    if custom_field.get("customized_type"):
        lines.append(
            messages.label_customized_type.format(value=custom_field["customized_type"])
        )
    if custom_field.get("field_format"):
        lines.append(
            messages.label_field_format.format(value=custom_field["field_format"])
        )
    lines.append(
        messages.label_is_required.format(
            value=_format_bool(bool(custom_field.get("is_required")))
        )
    )
    if custom_field.get("default_value"):
        lines.append(
            messages.label_default_value.format(value=custom_field["default_value"])
        )
    if custom_field.get("regexp"):
        lines.append(messages.label_regexp.format(value=custom_field["regexp"]))
    if custom_field.get("min_length") is not None:
        lines.append(messages.label_min_length.format(value=custom_field["min_length"]))
    if custom_field.get("max_length") is not None:
        lines.append(messages.label_max_length.format(value=custom_field["max_length"]))
    possible_values = custom_field.get("possible_values") or []
    if possible_values:
        lines.append(messages.label_possible_values_header)
        for pv in possible_values:
            lines.append(f"  {_format_possible_value(pv)}")
    trackers = custom_field.get("trackers") or []
    if trackers:
        lines.append(messages.label_trackers_header)
        for tracker in trackers:
            lines.append(f"  {tracker['id']} {tracker['name']}")
    roles = custom_field.get("roles") or []
    if roles:
        lines.append(messages.label_roles_header)
        for role in roles:
            lines.append(f"  {role['id']} {role['name']}")
    print("\n".join(lines))


def _handle_custom_field_view(
    items: Sequence[Mapping[str, Any]], args: argparse.Namespace
) -> bool:
    """view が選ばれていれば 1 件表示して True を返す。"""
    if resolve_alias(getattr(args, "custom_field_command", None)) != "view":
        return False
    # /custom_fields/:id.json が無いので一覧から絞り込む
    custom_field = find_custom_field(
        cast(list[CustomField], list(items)), args.custom_field_id
    )
    if custom_field is None:
        print(messages.custom_field_not_found.format(id=args.custom_field_id))
        sys.exit(1)
    _print_custom_field(custom_field, args.full)
    return True


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
        add_subcommands=_add_custom_field_view_parser,
        handle_subcommand=_handle_custom_field_view,
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
) -> argparse._SubParsersAction:
    """リソースに list (alias: l) サブコマンドを追加し、その subparsers を返す

    引数無しの呼び出しと同じ挙動になるよう、handle 側では dest を参照しない。
    cached なリソースは応答をキャッシュするので --refresh も受け付ける。
    戻り値の subparsers に list 以外のサブコマンドを足せる。
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
    return subparsers


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
        list_subparsers = _add_list_subparser(parser, resource, parents)
        if resource.add_subcommands is not None:
            resource.add_subcommands(list_subparsers, parents)


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
    if resource.handle_subcommand is not None and resource.handle_subcommand(
        items, args
    ):
        return
    _print_enumeration(items, args.full, resource)
