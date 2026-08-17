import argparse
import json
import sys

import requests

from redi import config
from redi.api.exceptions import print_http_error_body
from redi.api.membership import Membership, MembershipNotFoundException
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.shared_options import project_option_parser
from redi.i18n import messages
from redi.service import membership_service


def _parse_role_ids(value: str) -> list[int]:
    return [int(v) for v in value.split(",") if v.strip()]


def _format_membership_line(membership: Membership) -> str:
    """メンバーシップ 1 件を `id [user|group] <principal> - <roles>` の 1 行にする。"""
    principal = membership.get("user") or membership.get("group") or {}
    principal_kind = "user" if "user" in membership else "group"
    principal_str = f"{principal.get('id', '?')} {principal.get('name', '')}".strip()
    roles = membership.get("roles") or []
    role_str = ", ".join(r.get("name", "") for r in roles)
    return f"{membership['id']} [{principal_kind}] {principal_str} - {role_str}"


def _list_memberships(project_id: str, full: bool = False) -> None:
    """メンバーシップ一覧を標準出力に出す。full=True では取得した JSON をそのまま出す。"""
    memberships = membership_service.list_memberships(project_id)
    if full:
        print(json.dumps(memberships, ensure_ascii=False))
        return
    for membership in memberships:
        print(_format_membership_line(membership))


def _read_membership(membership_id: str) -> Membership:
    """メンバーシップを取得する。存在しない場合は exit 1。"""
    try:
        return membership_service.read_membership(membership_id)
    except MembershipNotFoundException:
        print(messages.membership_not_found.format(id=membership_id))
        sys.exit(1)


def _view_membership(membership_id: str, full: bool = False) -> None:
    """メンバーシップの詳細を標準出力に出す。存在しない場合は exit 1。"""
    membership = _read_membership(membership_id)
    if full:
        print(json.dumps(membership, ensure_ascii=False))
        return
    lines = [_format_membership_line(membership)]
    project = membership.get("project")
    if project:
        lines.append(
            messages.label_project_field.format(
                id=project.get("id"), name=project.get("name", "")
            )
        )
    roles = membership.get("roles") or []
    if roles:
        lines.append(messages.label_roles_header)
        for r in roles:
            inherited = messages.label_inherited_suffix if r.get("inherited") else ""
            lines.append(f"  {r.get('id')} {r.get('name', '')}{inherited}")
    print("\n".join(lines))


def _create_membership(project_id: str, principal_id: int, role_ids: list[int]) -> None:
    """メンバーシップを追加し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        created = membership_service.create_membership(
            project_id, principal_id, role_ids
        )
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.membership_create_failed)
        sys.exit(1)
    print(messages.membership_created.format(line=_format_membership_line(created)))


def _update_membership(membership_id: str, role_ids: list[int]) -> None:
    """メンバーシップのロールを更新し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        membership_service.update_membership(membership_id, role_ids)
    except MembershipNotFoundException:
        print(messages.membership_not_found.format(id=membership_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.membership_update_failed)
        sys.exit(1)
    print(messages.membership_updated.format(id=membership_id))


def _delete_membership(membership_id: str) -> None:
    """メンバーシップを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        membership_service.delete_membership(membership_id)
    except MembershipNotFoundException:
        print(messages.membership_not_found.format(id=membership_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.membership_delete_failed)
        sys.exit(1)
    print(messages.membership_deleted.format(id=membership_id))


def add_membership_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    m_parser = subparsers.add_parser(
        "membership",
        aliases=["m"],
        help=messages.arg_help_membership_command,
        parents=[*parents, project_option_parser()],
    )
    m_subparsers = m_parser.add_subparsers(dest="membership_command")
    m_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_membership_list,
        parents=[*parents, project_option_parser(postfix=True)],
    )

    m_view_parser = m_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_membership_view, parents=parents
    )
    m_view_parser.add_argument(
        "membership_id", help=messages.arg_help_membership_view_id
    )
    m_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )

    m_create_parser = m_subparsers.add_parser(
        "create",
        aliases=["c"],
        help=messages.arg_help_membership_create,
        parents=parents,
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
        "update",
        aliases=["u"],
        help=messages.arg_help_membership_update,
        parents=parents,
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
        "delete",
        aliases=["d"],
        help=messages.arg_help_membership_delete,
        parents=parents,
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
        _view_membership(args.membership_id, full=args.full)
        return
    if cmd == "create":
        project_id = args.project_id or config.default_project_id
        if not project_id:
            print(messages.project_id_required)
            sys.exit(1)
        if args.user_id is None and args.group_id is None:
            print(messages.user_or_group_flag_required)
            sys.exit(1)
        principal_id = args.user_id if args.user_id is not None else args.group_id
        _create_membership(
            project_id=project_id,
            principal_id=principal_id,
            role_ids=_parse_role_ids(args.role_ids),
        )
        return
    if cmd == "update":
        role_ids = _parse_role_ids(args.role_ids)
        if not role_ids:
            print(messages.update_canceled)
            sys.exit()
        _update_membership(membership_id=args.membership_id, role_ids=role_ids)
        return
    if cmd == "delete":
        if not args.yes:
            m = _read_membership(args.membership_id)
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
        _delete_membership(args.membership_id)
        return

    if cmd == "list" or cmd is None:
        project_id = args.project_id or config.default_project_id
        if not project_id:
            print(messages.project_id_required)
            sys.exit(1)
        _list_memberships(project_id, full=args.full)
