import argparse

from redi.i18n import messages


def _add_list_subparser(
    parser: argparse.ArgumentParser,
    dest: str,
    help_: str,
    parents: list[argparse.ArgumentParser],
) -> None:
    """一覧専用リソースに list (alias: l) サブコマンドを追加する

    引数無しの呼び出しと同じ挙動になるよう、handle 側では dest を参照しない。
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
    _add_list_subparser(
        tracker_parser, "tracker_command", messages.arg_help_tracker_list, parents
    )


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
    _add_list_subparser(
        issue_status_parser,
        "issue_status_command",
        messages.arg_help_issue_status_list,
        parents,
    )


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
    _add_list_subparser(
        ip_parser,
        "issue_priority_command",
        messages.arg_help_issue_priority_list,
        parents,
    )


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
    _add_list_subparser(
        tea_parser,
        "time_entry_activity_command",
        messages.arg_help_time_entry_activity_list,
        parents,
    )


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
    _add_list_subparser(
        dc_parser,
        "document_category_command",
        messages.arg_help_document_category_list,
        parents,
    )


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
    _add_list_subparser(
        cf_parser,
        "custom_field_command",
        messages.arg_help_custom_field_list,
        parents,
    )
