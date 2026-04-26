import argparse

from redi.cli._common import confirm_delete_with_identifier, resolve_alias
from redi.i18n import messages
from redi.api.project import (
    archive_project,
    create_project,
    delete_project,
    fetch_project,
    list_projects,
    read_project,
    unarchive_project,
    update_project,
)


def add_project_parser(subparsers: argparse._SubParsersAction) -> None:
    p_parser = subparsers.add_parser(
        "project",
        aliases=["p"],
        help=messages.arg_help_project_command,
    )
    p_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    p_subparsers = p_parser.add_subparsers(dest="project_command")
    p_subparsers.add_parser("list", aliases=["l"], help=messages.arg_help_project_list)
    p_view_parser = p_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_project_view
    )
    p_view_parser.add_argument("project_id", help=messages.arg_help_project_view_id)
    p_view_parser.add_argument(
        "--include",
        help=messages.arg_help_project_include,
    )
    p_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    p_view_parser.add_argument(
        "--web", "-w", action="store_true", help=messages.arg_help_open_web
    )
    p_create_parser = p_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_project_create
    )
    p_create_parser.add_argument("name", help=messages.arg_help_project_name)
    p_create_parser.add_argument(
        "identifier", help=messages.arg_help_project_identifier
    )
    p_create_parser.add_argument(
        "--description", "-d", help=messages.arg_help_description
    )
    p_create_parser.add_argument(
        "--is_public",
        choices=["true", "false"],
        help=messages.arg_help_project_is_public,
    )
    p_create_parser.add_argument("--parent_id", help=messages.arg_help_parent_id)
    p_create_parser.add_argument("--tracker_ids", help=messages.arg_help_tracker_ids)
    p_delete_parser = p_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_project_delete
    )
    p_delete_parser.add_argument("project_id", help=messages.arg_help_project_delete_id)
    p_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )
    p_update_parser = p_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_project_update
    )
    p_update_parser.add_argument("project_id", help=messages.arg_help_project_update_id)
    p_update_parser.add_argument("--name", "-n", help=messages.arg_help_project_name)
    p_update_parser.add_argument(
        "--description", "-d", help=messages.arg_help_description
    )
    p_update_parser.add_argument(
        "--is_public",
        choices=["true", "false"],
        help=messages.arg_help_project_is_public,
    )
    p_update_parser.add_argument("--parent_id", help=messages.arg_help_parent_id)
    p_update_parser.add_argument("--tracker_ids", help=messages.arg_help_tracker_ids)
    p_update_parser.add_argument(
        "--archive",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=messages.arg_help_project_archive,
    )


def handle_project(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.project_command)
    if cmd == "view":
        read_project(
            args.project_id,
            include=args.include or "",
            full=args.full,
            web=args.web,
        )
    elif cmd == "create":
        is_public = None
        if args.is_public is not None:
            is_public = args.is_public == "true"
        tracker_ids = None
        if args.tracker_ids:
            tracker_ids = [int(x) for x in args.tracker_ids.split(",")]
        create_project(
            name=args.name,
            identifier=args.identifier,
            description=args.description,
            is_public=is_public,
            parent_id=args.parent_id,
            tracker_ids=tracker_ids,
        )
    elif cmd == "delete":
        if not args.yes:
            project = fetch_project(args.project_id)
            summary = (
                messages.delete_target_project.format(
                    id=project["id"],
                    name=project["name"],
                    identifier=project["identifier"],
                )
                + "\n"
                + messages.delete_project_warning
            )
            confirm_delete_with_identifier(
                summary, project["identifier"], messages.label_project_identifier
            )
        delete_project(args.project_id)
    elif cmd == "update":
        is_public = None
        if args.is_public is not None:
            is_public = args.is_public == "true"
        tracker_ids = None
        if args.tracker_ids:
            tracker_ids = [int(x) for x in args.tracker_ids.split(",")]
        should_update = (
            args.name is not None
            or args.description is not None
            or is_public is not None
            or args.parent_id is not None
            or tracker_ids is not None
        )
        if should_update:
            update_project(
                project_id=args.project_id,
                name=args.name,
                description=args.description,
                is_public=is_public,
                parent_id=args.parent_id,
                tracker_ids=tracker_ids,
            )
        if args.archive is True:
            archive_project(args.project_id)
        elif args.archive is False:
            unarchive_project(args.project_id)
        elif not should_update:
            print(messages.update_canceled)
            exit()
    elif cmd == "list" or cmd is None:
        list_projects(full=args.full)
