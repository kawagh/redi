import argparse

from redi.api.issue_relation import RELATION_TYPES
from redi.cli.shared_options import SharedOptionParser, add_full_argument
from redi.i18n import messages


def _issue_list_option_parser(*, postfix: bool = False) -> argparse.ArgumentParser:
    """issue の一覧フィルタと出力形式のオプション"""
    parser = SharedOptionParser(postfix=postfix)
    parser.add_argument("--full", action="store_true", help=messages.arg_help_full_json)
    parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_issue_filter_project
    )
    parser.add_argument(
        "--version",
        "-v",
        help=messages.arg_help_issue_filter_version,
    )
    parser.add_argument(
        "--assigned_to",
        "-a",
        help=messages.arg_help_issue_filter_assigned_to,
    )
    parser.add_argument(
        "--status_id",
        "-s",
        help=messages.arg_help_issue_filter_status,
    )
    parser.add_argument(
        "--tracker_id", "-t", help=messages.arg_help_issue_filter_tracker
    )
    parser.add_argument("--priority_id", help=messages.arg_help_issue_filter_priority)
    parser.add_argument(
        "--query_id",
        "-q",
        help=messages.arg_help_issue_filter_query,
    )
    parser.add_argument("--limit", "-l", type=int, help=messages.arg_help_limit)
    parser.add_argument("--offset", "-o", type=int, help=messages.arg_help_offset)
    return parser


def add_issue_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    i_parser = subparsers.add_parser(
        "issue",
        aliases=["i"],
        help=messages.arg_help_issue_command,
        parents=[*parents, _issue_list_option_parser()],
    )
    i_subparsers = i_parser.add_subparsers(dest="issue_command")
    i_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_issue_list,
        parents=[*parents, _issue_list_option_parser(postfix=True)],
    )
    i_view_parser = i_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_issue_view, parents=parents
    )
    i_view_parser.add_argument("issue_id", help=messages.arg_help_issue_view_id)
    i_view_parser.add_argument(
        "--include",
        help=messages.arg_help_issue_include,
    )
    add_full_argument(i_view_parser, postfix=True)
    i_view_parser.add_argument(
        "--web", "-w", action="store_true", help=messages.arg_help_open_web
    )
    i_create_parser = i_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_issue_create, parents=parents
    )
    i_create_parser.add_argument(
        "subject", nargs="?", help=messages.arg_help_issue_subject_arg
    )
    i_create_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_project_id
    )
    i_create_parser.add_argument(
        "--tracker_id", "-t", help=messages.arg_help_issue_tracker_id
    )
    i_create_parser.add_argument(
        "--priority_id", help=messages.arg_help_issue_priority_id
    )
    i_create_parser.add_argument(
        "--assigned_to_id", "-a", help=messages.arg_help_issue_assigned_to_id
    )
    i_create_parser.add_argument(
        "--fixed_version_id", help=messages.arg_help_issue_fixed_version_id
    )
    i_create_parser.add_argument(
        "--parent_issue_id", help=messages.arg_help_issue_parent
    )
    i_create_parser.add_argument(
        "--start_date", help=messages.arg_help_issue_start_date
    )
    i_create_parser.add_argument("--due_date", help=messages.arg_help_issue_due_date)
    i_create_parser.add_argument(
        "--estimated_hours", type=float, help=messages.arg_help_issue_estimated_hours
    )
    i_create_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help=messages.arg_help_issue_description,
    )
    i_create_parser.add_argument(
        "--custom_fields",
        help=messages.arg_help_custom_fields,
    )
    add_full_argument(i_create_parser, postfix=True)
    i_update_parser = i_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_issue_update, parents=parents
    )
    i_update_parser.add_argument(
        "issue_id", nargs="?", help=messages.arg_help_issue_update_id
    )
    i_update_parser.add_argument(
        "--subject", "-s", help=messages.arg_help_issue_subject_opt
    )
    i_update_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help=messages.arg_help_issue_update_description,
    )
    # `issue list` の `-p` はフィルタなので、誤ってイシューを移動させないよう短縮形は付けない
    i_update_parser.add_argument(
        "--project_id", help=messages.arg_help_issue_update_project_id
    )
    i_update_parser.add_argument(
        "--tracker_id", "-t", help=messages.arg_help_issue_update_tracker_id
    )
    i_update_parser.add_argument("--status_id", help=messages.arg_help_issue_status_id)
    i_update_parser.add_argument(
        "--priority_id", help=messages.arg_help_issue_priority_id
    )
    i_update_parser.add_argument(
        "--assigned_to_id", "-a", help=messages.arg_help_issue_assigned_to_id
    )
    i_update_parser.add_argument(
        "--fixed_version_id", help=messages.arg_help_issue_fixed_version_id
    )
    i_update_parser.add_argument(
        "--parent_issue_id", help=messages.arg_help_issue_parent
    )
    i_update_parser.add_argument(
        "--start_date", help=messages.arg_help_issue_start_date
    )
    i_update_parser.add_argument("--due_date", help=messages.arg_help_issue_due_date)
    i_update_parser.add_argument(
        "--done_ratio", type=int, help=messages.arg_help_issue_done_ratio
    )
    i_update_parser.add_argument(
        "--estimated_hours", type=float, help=messages.arg_help_issue_estimated_hours
    )
    i_update_parser.add_argument("--notes", "-n", help=messages.arg_help_issue_notes)
    i_update_parser.add_argument(
        "--custom_fields",
        help=messages.arg_help_custom_fields,
    )
    i_update_parser.add_argument(
        "--relate",
        choices=RELATION_TYPES,
        help=messages.arg_help_issue_relate,
    )
    i_update_parser.add_argument(
        "--to", dest="relate_to", help=messages.arg_help_issue_relate_to
    )
    i_update_parser.add_argument(
        "--delete-relation",
        action="store_true",
        help=messages.arg_help_issue_delete_relation,
    )
    i_update_parser.add_argument(
        "--attach",
        action="append",
        help=messages.arg_help_issue_attach,
    )
    i_update_parser.add_argument(
        "--hours", type=float, help=messages.arg_help_issue_hours
    )
    i_update_parser.add_argument(
        "--activity_id", help=messages.arg_help_issue_activity_id
    )
    i_update_parser.add_argument("--spent_on", help=messages.arg_help_issue_spent_on)
    i_update_parser.add_argument(
        "--time_comments", help=messages.arg_help_issue_time_comments
    )
    i_update_parser.add_argument(
        "--add-watcher",
        type=int,
        action="append",
        dest="add_watcher_ids",
        help=messages.arg_help_issue_add_watcher,
    )
    i_update_parser.add_argument(
        "--remove-watcher",
        type=int,
        action="append",
        dest="remove_watcher_ids",
        help=messages.arg_help_issue_remove_watcher,
    )
    i_comment_parser = i_subparsers.add_parser(
        "comment", aliases=["co"], help=messages.arg_help_issue_comment, parents=parents
    )
    i_comment_parser.add_argument("issue_id", help=messages.arg_help_issue_view_id)
    i_comment_parser.add_argument(
        "notes", nargs="?", default="", help=messages.arg_help_issue_comment_notes
    )
    i_delete_parser = i_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_issue_delete, parents=parents
    )
    i_delete_parser.add_argument("issue_id", help=messages.arg_help_issue_view_id)
    i_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )
