import argparse

from redi.cli._common import confirm_delete, resolve_alias
from redi.config import default_project_id
from redi.i18n import messages
from redi.api.membership import (
    create_membership,
    delete_membership,
    fetch_membership,
    list_memberships,
    read_membership,
    update_membership,
)


def _parse_role_ids(value: str) -> list[int]:
    return [int(v) for v in value.split(",") if v.strip()]


def add_membership_parser(subparsers: argparse._SubParsersAction) -> None:
    m_parser = subparsers.add_parser(
        "membership",
        aliases=["m"],
        help=messages.arg_help_membership_command,
    )
    m_parser.add_argument("--project_id", "-p", help=messages.arg_help_project_id)
    m_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    m_subparsers = m_parser.add_subparsers(dest="membership_command")
    m_subparsers.add_parser(
        "list", aliases=["l"], help=messages.arg_help_membership_list
    )

    m_view_parser = m_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_membership_view
    )
    m_view_parser.add_argument(
        "membership_id", help=messages.arg_help_membership_view_id
    )
    m_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )

    m_create_parser = m_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_membership_create
    )
    m_create_parser.add_argument(
        "--project_id", "-p", help=messages.arg_help_project_id
    )
    m_create_parser.add_argument(
        "--user_id", "-u", type=int, help=messages.arg_help_membership_user_id
    )
    m_create_parser.add_argument(
        "--group_id", "-g", type=int, help=messages.arg_help_membership_group_id
    )
    m_create_parser.add_argument(
        "--role_ids",
        "-r",
        required=True,
        help=messages.arg_help_membership_role_ids,
    )

    m_update_parser = m_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_membership_update
    )
    m_update_parser.add_argument(
        "membership_id", help=messages.arg_help_membership_update_id
    )
    m_update_parser.add_argument(
        "--role_ids",
        "-r",
        required=True,
        help=messages.arg_help_membership_role_ids,
    )

    m_delete_parser = m_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_membership_delete
    )
    m_delete_parser.add_argument(
        "membership_id", help=messages.arg_help_membership_delete_id
    )
    m_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def handle_membership(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.membership_command)
    if cmd == "view":
        read_membership(args.membership_id, full=args.full)
        return
    if cmd == "create":
        project_id = args.project_id or default_project_id
        if not project_id:
            print(messages.project_id_required)
            exit(1)
        if args.user_id is None and args.group_id is None:
            print(messages.user_or_group_flag_required)
            exit(1)
        create_membership(
            project_id=project_id,
            role_ids=_parse_role_ids(args.role_ids),
            user_id=args.user_id,
            group_id=args.group_id,
        )
        return
    if cmd == "update":
        update_membership(
            membership_id=args.membership_id,
            role_ids=_parse_role_ids(args.role_ids),
        )
        return
    if cmd == "delete":
        if not args.yes:
            m = fetch_membership(args.membership_id)
            principal = m.get("user") or m.get("group") or {}
            kind = "user" if "user" in m else "group"
            roles = ", ".join(r.get("name", "") for r in (m.get("roles") or []))
            confirm_delete(
                messages.delete_target_membership.format(
                    id=m["id"],
                    kind=kind,
                    principal_id=principal.get("id", "?"),
                    principal_name=principal.get("name", ""),
                    roles=roles,
                )
            )
        delete_membership(args.membership_id)
        return

    if cmd == "list" or cmd is None:
        project_id = args.project_id or default_project_id
        if not project_id:
            print(messages.project_id_required)
            exit(1)
        list_memberships(project_id, full=args.full)
