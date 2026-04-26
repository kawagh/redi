import argparse

from redi.cli._common import confirm_delete, resolve_alias
from redi.config import default_project_id
from redi.i18n import messages
from redi.api.issue_category import (
    create_issue_category,
    delete_issue_category,
    fetch_issue_category,
    list_issue_categories,
    read_issue_category,
    update_issue_category,
)


def add_issue_category_parser(subparsers: argparse._SubParsersAction) -> None:
    ic_parser = subparsers.add_parser(
        "issue_category",
        help=messages.arg_help_issue_category_command,
    )
    ic_parser.add_argument("--project_id", "-p", help=messages.arg_help_project_id)
    ic_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    ic_subparsers = ic_parser.add_subparsers(dest="issue_category_command")
    ic_subparsers.add_parser(
        "list", aliases=["l"], help=messages.arg_help_issue_category_list
    )

    ic_view_parser = ic_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_issue_category_view
    )
    ic_view_parser.add_argument(
        "category_id", help=messages.arg_help_issue_category_view_id
    )
    ic_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )

    ic_create_parser = ic_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_issue_category_create
    )
    ic_create_parser.add_argument("name", help=messages.arg_help_issue_category_name)
    ic_create_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_project_id
    )
    ic_create_parser.add_argument(
        "--assigned_to_id",
        type=int,
        help=messages.arg_help_issue_category_assigned_to_id,
    )

    ic_update_parser = ic_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_issue_category_update
    )
    ic_update_parser.add_argument(
        "category_id", help=messages.arg_help_issue_category_update_id
    )
    ic_update_parser.add_argument(
        "--name", "-n", help=messages.arg_help_issue_category_name_opt
    )
    ic_update_parser.add_argument(
        "--assigned_to_id",
        type=int,
        help=messages.arg_help_issue_category_assigned_to_id,
    )

    ic_delete_parser = ic_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_issue_category_delete
    )
    ic_delete_parser.add_argument(
        "category_id", help=messages.arg_help_issue_category_delete_id
    )
    ic_delete_parser.add_argument(
        "--reassign_to_id",
        type=int,
        help=messages.arg_help_issue_category_reassign_to_id,
    )
    ic_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def handle_issue_category(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.issue_category_command)
    if cmd == "view":
        read_issue_category(args.category_id, full=args.full)
        return
    if cmd == "create":
        project_id = args.project_id or default_project_id
        if not project_id:
            print(messages.project_id_required)
            exit(1)
        create_issue_category(
            project_id=project_id,
            name=args.name,
            assigned_to_id=args.assigned_to_id,
        )
        return
    if cmd == "update":
        update_issue_category(
            category_id=args.category_id,
            name=args.name,
            assigned_to_id=args.assigned_to_id,
        )
        return
    if cmd == "delete":
        if not args.yes:
            category = fetch_issue_category(args.category_id)
            confirm_delete(
                messages.delete_target_category.format(
                    id=category["id"], name=category["name"]
                )
            )
        delete_issue_category(
            category_id=args.category_id,
            reassign_to_id=args.reassign_to_id,
        )
        return
    if cmd == "list" or cmd is None:
        project_id = args.project_id or default_project_id
        if not project_id:
            print(messages.project_id_required)
            exit(1)
        list_issue_categories(project_id, full=args.full)
