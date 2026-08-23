import argparse
import json
import sys
from collections.abc import Iterable, Mapping
from typing import Any

from redi.api.custom_field import CustomField, fetch_custom_fields, find_custom_field
from redi.api.enumeration import (
    fetch_document_categories,
    fetch_issue_priorities,
    fetch_time_entry_activities,
)
from redi.api.issue_status import fetch_issue_statuses
from redi.api.query import fetch_queries
from redi.api.tracker import fetch_trackers
from redi.cli.alias import resolve_alias
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
) -> argparse._SubParsersAction:
    """リソースに list (alias: l) サブコマンドを追加し、その subparsers を返す

    引数無しの呼び出しと同じ挙動になるよう、handle 側では dest を参照しない。
    cached=True のリソースは応答をキャッシュするので --refresh も受け付ける。
    戻り値の subparsers に list 以外のサブコマンドを足せる。
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
    cf_subparsers = _add_list_subparser(
        cf_parser,
        "custom_field_command",
        messages.arg_help_custom_field_list,
        parents,
        cached=True,
    )
    cf_view_parser = cf_subparsers.add_parser(
        "view",
        aliases=["v"],
        help=messages.arg_help_custom_field_view,
        parents=parents,
    )
    cf_view_parser.add_argument(
        "custom_field_id", help=messages.arg_help_custom_field_view_id
    )
    cf_view_parser.add_argument(
        "--full",
        action="store_true",
        # 未指定時に親パーサの --full を上書きしないようにする
        default=argparse.SUPPRESS,
        help=messages.arg_help_full_json,
    )
    _add_refresh_option(cf_view_parser, postfix=True)


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


def handle_custom_field(args: argparse.Namespace) -> None:
    custom_fields = fetch_custom_fields(refresh=args.refresh)
    if custom_fields is None:
        print(messages.custom_field_admin_required)
        sys.exit(1)
    if resolve_alias(args.custom_field_command) == "view":
        # /custom_fields/:id.json が無いので一覧から絞り込む
        custom_field = find_custom_field(custom_fields, args.custom_field_id)
        if custom_field is None:
            print(messages.custom_field_not_found.format(id=args.custom_field_id))
            sys.exit(1)
        _print_custom_field(custom_field, args.full)
        return
    _print_id_name_list(custom_fields, args.full)
