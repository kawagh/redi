"""`group` サブコマンドの表示整形。

取得と更新は `service.group_service` に任せ、ここでは print と sys.exit を担当する。
"""

import argparse
import json
import sys
from typing import NoReturn

import requests

from redi.api.exceptions import print_http_error_body
from redi.api.group import (
    Group,
    GroupAdminRequiredException,
    GroupNotFoundException,
    GroupUserNotFoundException,
)
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.shared_options import add_format_options, full_option_parser, wants_json
from redi.i18n import messages
from redi.output import eprint
from redi.service import group_service


def _exit_group_not_found(group_id: str) -> NoReturn:
    eprint(messages.group_not_found.format(id=group_id))
    sys.exit(1)


def _exit_http_error(e: requests.exceptions.HTTPError, message: str) -> NoReturn:
    eprint(e)
    print_http_error_body(e)
    eprint(message)
    sys.exit(1)


def _list_groups(full: bool = False) -> None:
    """グループ一覧を1行ずつ出す。full=True では取得した JSON をそのまま出す。"""
    groups = group_service.list_groups()
    if full:
        print(json.dumps(groups, ensure_ascii=False))
        return
    for group in groups:
        print(f"{group['id']} {group['name']}")


def _format_group(group: Group) -> str:
    """グループの詳細を表示用の文字列に整形する。"""
    lines = [f"{group['id']} {group['name']}"]
    users = group.get("users") or []
    if users:
        lines.append("")
        lines.append(messages.label_users_header)
        for u in users:
            lines.append(f"  {u['id']} {u['name']}")
    memberships = group.get("memberships") or []
    if memberships:
        lines.append("")
        lines.append(messages.label_membership_header)
        for m in memberships:
            project = m.get("project") or {}
            roles = m.get("roles") or []
            role_names = ", ".join(r.get("name", "") for r in roles)
            lines.append(
                f"  {project.get('id')} {project.get('name', '')} [{role_names}]"
            )
    return "\n".join(lines)


def _view_group(group_id: str, full: bool = False) -> None:
    """グループの詳細を標準出力に出す。存在しない場合は exit 1。"""
    try:
        group = group_service.read_group(group_id, include="users,memberships")
    except GroupNotFoundException:
        _exit_group_not_found(group_id)
    except GroupAdminRequiredException:
        eprint(messages.group_get_admin_required)
        sys.exit(1)
    if full:
        print(json.dumps(group, ensure_ascii=False))
        return
    print(_format_group(group))


def _create_group(name: str, user_ids: list[int] | None = None) -> None:
    """グループを作成し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        created = group_service.create_group(name, user_ids=user_ids)
    except GroupAdminRequiredException:
        eprint(messages.group_create_admin_required)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        _exit_http_error(e, messages.group_create_failed)
    print(
        messages.group_created.format(
            id=created["id"],
            name=created["name"],
            url=group_service.group_url(created["id"]),
        )
    )


def _update_group(
    group_id: str,
    name: str | None = None,
    user_ids: list[int] | None = None,
) -> None:
    """グループを更新し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        group_service.update_group(group_id, name=name, user_ids=user_ids)
    except GroupNotFoundException:
        _exit_group_not_found(group_id)
    except GroupAdminRequiredException:
        eprint(messages.group_update_admin_required)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        _exit_http_error(e, messages.group_update_failed)
    print(messages.group_updated.format(id=group_id))


def _add_group_user(group_id: str, user_id: int) -> None:
    """グループにユーザーを追加し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        group_service.add_group_user(group_id, user_id)
    except GroupNotFoundException:
        _exit_group_not_found(group_id)
    except GroupAdminRequiredException:
        eprint(messages.group_add_user_admin_required)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        _exit_http_error(e, messages.group_add_user_failed)
    print(messages.group_user_added.format(group_id=group_id, user_id=user_id))


def _remove_group_user(group_id: str, user_id: int) -> None:
    """グループからユーザーを外し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        group_service.remove_group_user(group_id, user_id)
    except GroupUserNotFoundException:
        eprint(
            messages.group_or_user_not_found.format(group_id=group_id, user_id=user_id)
        )
        sys.exit(1)
    except GroupAdminRequiredException:
        eprint(messages.group_remove_user_admin_required)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        _exit_http_error(e, messages.group_remove_user_failed)
    print(messages.group_user_removed.format(group_id=group_id, user_id=user_id))


def _delete_group(group_id: str) -> None:
    """グループを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        group_service.delete_group(group_id)
    except GroupNotFoundException:
        _exit_group_not_found(group_id)
    except GroupAdminRequiredException:
        eprint(messages.group_delete_admin_required)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        _exit_http_error(e, messages.group_delete_failed)
    print(messages.group_deleted.format(id=group_id))


def add_group_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    group_parser = subparsers.add_parser(
        "group",
        aliases=["g"],
        help=messages.arg_help_group_command,
        parents=[*parents, full_option_parser()],
    )
    group_subparsers = group_parser.add_subparsers(dest="group_command")
    group_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_group_list,
        parents=[*parents, full_option_parser(postfix=True)],
    )
    g_view_parser = group_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_group_view, parents=parents
    )
    g_view_parser.add_argument("group_id", help=messages.arg_help_group_view_id)
    add_format_options(g_view_parser)
    g_create_parser = group_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_group_create, parents=parents
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
        "update", aliases=["u"], help=messages.arg_help_group_update, parents=parents
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
        "delete", aliases=["d"], help=messages.arg_help_group_delete, parents=parents
    )
    g_delete_parser.add_argument("group_id", help=messages.arg_help_group_delete_id)
    g_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def handle_group(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.group_command)
    if cmd == "view":
        _view_group(args.group_id, full=wants_json(args))
        return
    if cmd == "create":
        _create_group(name=args.name, user_ids=args.user_ids)
        return
    if cmd == "update":
        should_update = args.name is not None or args.user_ids is not None
        if should_update:
            _update_group(
                group_id=args.group_id,
                name=args.name,
                user_ids=args.user_ids,
            )
        for user_id in args.add_user_ids or []:
            _add_group_user(args.group_id, user_id)
        for user_id in args.remove_user_ids or []:
            _remove_group_user(args.group_id, user_id)
        if not should_update and not args.add_user_ids and not args.remove_user_ids:
            print(messages.update_canceled)
            sys.exit()
        return
    if cmd == "delete":
        if not args.yes:
            try:
                group = group_service.read_group(args.group_id)
            except GroupNotFoundException:
                _exit_group_not_found(args.group_id)
            except GroupAdminRequiredException:
                eprint(messages.group_get_admin_required)
                sys.exit(1)
            confirm_delete(
                messages.delete_target_group.format(id=group["id"], name=group["name"])
            )
        _delete_group(args.group_id)
        return
    if cmd == "list" or cmd is None:
        _list_groups(full=wants_json(args))
