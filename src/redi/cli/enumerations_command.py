import argparse

from redi.i18n import messages


def add_tracker_parser(subparsers: argparse._SubParsersAction) -> None:
    tracker_parser = subparsers.add_parser(
        "tracker", help=messages.arg_help_tracker_command
    )
    tracker_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def add_issue_status_parser(subparsers: argparse._SubParsersAction) -> None:
    issue_status_parser = subparsers.add_parser(
        "issue_status", help=messages.arg_help_issue_status_command
    )
    issue_status_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def add_issue_priority_parser(subparsers: argparse._SubParsersAction) -> None:
    ip_parser = subparsers.add_parser(
        "issue_priority", help=messages.arg_help_issue_priority_command
    )
    ip_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def add_time_entry_activity_parser(subparsers: argparse._SubParsersAction) -> None:
    tea_parser = subparsers.add_parser(
        "time_entry_activity", help=messages.arg_help_time_entry_activity_command
    )
    tea_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def add_document_category_parser(subparsers: argparse._SubParsersAction) -> None:
    dc_parser = subparsers.add_parser(
        "document_category", help=messages.arg_help_document_category_command
    )
    dc_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def add_query_parser(subparsers: argparse._SubParsersAction) -> None:
    query_parser = subparsers.add_parser("query", help=messages.arg_help_query_command)
    query_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )


def add_custom_field_parser(subparsers: argparse._SubParsersAction) -> None:
    cf_parser = subparsers.add_parser(
        "custom_field", help=messages.arg_help_custom_field_command
    )
    cf_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
