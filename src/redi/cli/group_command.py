import argparse

from redi.cli._common import confirm_delete, resolve_alias
from redi.i18n import messages
from redi.api.group import (
    add_group_user,
    create_group,
    delete_group,
    fetch_group,
    list_groups,
    read_group,
    remove_group_user,
    update_group,
)


def add_group_parser(subparsers: argparse._SubParsersAction) -> None:
    group_parser = subparsers.add_parser(
        "group",
        help=messages.arg_help_group_command,
    )
    group_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    group_subparsers = group_parser.add_subparsers(dest="group_command")
    group_subparsers.add_parser(
        "list", aliases=["l"], help=messages.arg_help_group_list
    )
    g_view_parser = group_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_group_view
    )
    g_view_parser.add_argument("group_id", help=messages.arg_help_group_view_id)
    g_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    g_create_parser = group_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_group_create
    )
    g_create_parser.add_argument("name", help=messages.arg_help_group_name)
    g_create_parser.add_argument(
        "--user_id",
        type=int,
        action="append",
        dest="user_ids",
        help=messages.arg_help_group_user_id,
    )
    g_update_parser = group_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_group_update
    )
    g_update_parser.add_argument("group_id", help=messages.arg_help_group_update_id)
    g_update_parser.add_argument("--name", "-n", help=messages.arg_help_group_name_opt)
    g_update_parser.add_argument(
        "--user_id",
        type=int,
        action="append",
        dest="user_ids",
        help=messages.arg_help_group_user_id_replace,
    )
    g_update_parser.add_argument(
        "--add-user",
        type=int,
        action="append",
        dest="add_user_ids",
        help=messages.arg_help_group_add_user,
    )
    g_update_parser.add_argument(
        "--remove-user",
        type=int,
        action="append",
        dest="remove_user_ids",
        help=messages.arg_help_group_remove_user,
    )
    g_delete_parser = group_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_group_delete
    )
    g_delete_parser.add_argument("group_id", help=messages.arg_help_group_delete_id)
    g_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def handle_group(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.group_command)
    if cmd == "view":
        read_group(args.group_id, full=args.full)
        return
    if cmd == "create":
        create_group(name=args.name, user_ids=args.user_ids)
        return
    if cmd == "update":
        should_update = args.name is not None or args.user_ids is not None
        if should_update:
            update_group(
                group_id=args.group_id,
                name=args.name,
                user_ids=args.user_ids,
            )
        for user_id in args.add_user_ids or []:
            add_group_user(args.group_id, user_id)
        for user_id in args.remove_user_ids or []:
            remove_group_user(args.group_id, user_id)
        if not should_update and not args.add_user_ids and not args.remove_user_ids:
            print(messages.update_canceled)
            exit()
        return
    if cmd == "delete":
        if not args.yes:
            group = fetch_group(args.group_id)
            confirm_delete(
                messages.delete_target_group.format(id=group["id"], name=group["name"])
            )
        delete_group(args.group_id)
        return
    if cmd == "list" or cmd is None:
        list_groups(full=args.full)
