import argparse
import json
import sys

import requests

from redi.api.exceptions import print_http_error_body
from redi.api.user import User, UserNotFoundException, UserPermissionDeniedException
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete_with_identifier
from redi.cli.shared_options import SharedOptionParser
from redi.cli.user_format import format_user_detail, user_summary
from redi.i18n import messages
from redi.service import user_service

MAIL_NOTIFICATION_CHOICES = [
    "all",
    "selected",
    "only_my_events",
    "only_assigned",
    "only_owner",
    "none",
]


def _read_user(user_id: str, detail: bool = False) -> User:
    """ユーザーを取得する。存在しない場合や権限が無い場合は exit 1。"""
    try:
        return user_service.read_user(user_id, detail=detail)
    except UserNotFoundException:
        print(messages.user_not_found.format(id=user_id))
        sys.exit(1)
    except UserPermissionDeniedException:
        print(messages.user_detail_permission_required)
        sys.exit(1)


def _create_user(
    login: str,
    firstname: str,
    lastname: str,
    mail: str,
    password: str | None = None,
    auth_source_id: int | None = None,
    mail_notification: str | None = None,
    must_change_passwd: bool | None = None,
    generate_password: bool | None = None,
    admin: bool | None = None,
) -> None:
    """ユーザーを作成し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        created = user_service.create_user(
            login=login,
            firstname=firstname,
            lastname=lastname,
            mail=mail,
            password=password,
            auth_source_id=auth_source_id,
            mail_notification=mail_notification,
            must_change_passwd=must_change_passwd,
            generate_password=generate_password,
            admin=admin,
        )
    except UserPermissionDeniedException:
        print(messages.user_create_admin_required)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.user_create_failed)
        sys.exit(1)
    print(
        messages.user_created.format(
            id=created["id"],
            login=created["login"],
            url=user_service.user_url(created["id"]),
        )
    )


def _list_users(
    status: str | None = None,
    name: str | None = None,
    group_id: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
    full: bool = False,
) -> None:
    """ユーザー一覧を標準出力に出す。full=True では取得した JSON をそのまま出す。"""
    try:
        users = user_service.list_users(
            status=status, name=name, group_id=group_id, limit=limit, offset=offset
        )
    except UserPermissionDeniedException:
        print(messages.user_list_admin_required)
        print(messages.user_list_member_hint)
        return
    if full:
        print(json.dumps(users, ensure_ascii=False))
        return
    for user in users:
        print(f"{user['id']} {user['login']}")


def _view_user(user_id: str, full: bool = False) -> None:
    """ユーザーの詳細を標準出力に出す。full=True では取得した JSON をそのまま出す。"""
    user = _read_user(user_id, detail=True)
    if full:
        print(json.dumps(user, ensure_ascii=False))
        return
    print("\n".join(format_user_detail(user)))


def _update_user(
    user_id: str,
    login: str | None = None,
    firstname: str | None = None,
    lastname: str | None = None,
    mail: str | None = None,
    password: str | None = None,
    auth_source_id: int | None = None,
    mail_notification: str | None = None,
    must_change_passwd: bool | None = None,
    admin: bool | None = None,
) -> None:
    """ユーザーを更新し、結果を標準出力に出す。更新対象が無い場合や失敗時は exit 1。"""
    fields = {
        "login": login,
        "firstname": firstname,
        "lastname": lastname,
        "mail": mail,
        "password": password,
        "auth_source_id": auth_source_id,
        "mail_notification": mail_notification,
        "must_change_passwd": must_change_passwd,
        "admin": admin,
    }
    if all(value is None for value in fields.values()):
        print(messages.update_canceled_no_changes)
        sys.exit(1)
    try:
        user_service.update_user(
            user_id=user_id,
            login=login,
            firstname=firstname,
            lastname=lastname,
            mail=mail,
            password=password,
            auth_source_id=auth_source_id,
            mail_notification=mail_notification,
            must_change_passwd=must_change_passwd,
            admin=admin,
        )
    except UserNotFoundException:
        print(messages.user_not_found.format(id=user_id))
        sys.exit(1)
    except UserPermissionDeniedException:
        print(messages.user_update_admin_required)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.user_update_failed)
        sys.exit(1)
    print(messages.user_updated.format(id=user_id))


def _delete_user(user_id: str) -> None:
    """ユーザーを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        user_service.delete_user(user_id)
    except UserNotFoundException:
        print(messages.user_not_found.format(id=user_id))
        sys.exit(1)
    except UserPermissionDeniedException:
        print(messages.user_delete_admin_required)
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.user_delete_failed)
        sys.exit(1)
    print(messages.user_deleted.format(id=user_id))


def _user_list_option_parser(*, postfix: bool = False) -> argparse.ArgumentParser:
    """user の一覧フィルタと出力形式のオプション"""
    parser = SharedOptionParser(postfix=postfix)
    parser.add_argument(
        "--status",
        choices=user_service.USER_STATUS_CHOICES,
        help=messages.arg_help_user_status,
    )
    parser.add_argument("--name", help=messages.arg_help_user_name_filter)
    parser.add_argument("--group_id", type=int, help=messages.arg_help_user_group_id)
    parser.add_argument("--limit", type=int, help=messages.arg_help_limit)
    parser.add_argument("--offset", type=int, help=messages.arg_help_offset)
    parser.add_argument("--full", action="store_true", help=messages.arg_help_full_json)
    return parser


def add_user_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    u_parser = subparsers.add_parser(
        "user",
        aliases=["u"],
        help=messages.arg_help_user_command,
        parents=[*parents, _user_list_option_parser()],
    )
    u_subparsers = u_parser.add_subparsers(dest="user_command")
    u_subparsers.add_parser(
        "list",
        aliases=["l"],
        help=messages.arg_help_user_list,
        parents=[*parents, _user_list_option_parser(postfix=True)],
    )
    u_create_parser = u_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_user_create, parents=parents
    )
    u_create_parser.add_argument("login", help=messages.arg_help_user_login)
    u_create_parser.add_argument(
        "--firstname", "-f", required=True, help=messages.arg_help_user_firstname
    )
    u_create_parser.add_argument(
        "--lastname", "-l", required=True, help=messages.arg_help_user_lastname
    )
    u_create_parser.add_argument(
        "--mail", "-m", required=True, help=messages.arg_help_user_mail
    )
    u_create_parser.add_argument("--password", help=messages.arg_help_user_password)
    u_create_parser.add_argument(
        "--generate_password",
        action="store_true",
        help=messages.arg_help_user_generate_password,
    )
    u_create_parser.add_argument(
        "--auth_source_id", type=int, help=messages.arg_help_user_auth_source_id
    )
    u_create_parser.add_argument(
        "--mail_notification",
        choices=MAIL_NOTIFICATION_CHOICES,
        help=messages.arg_help_user_mail_notification,
    )
    u_create_parser.add_argument(
        "--must_change_passwd",
        action="store_true",
        help=messages.arg_help_user_must_change_passwd,
    )
    u_create_parser.add_argument(
        "--admin", action="store_true", help=messages.arg_help_user_admin
    )

    u_view_parser = u_subparsers.add_parser(
        "view", aliases=["v"], help=messages.arg_help_user_view, parents=parents
    )
    u_view_parser.add_argument("user_id", help=messages.arg_help_user_view_id)
    u_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )

    u_update_parser = u_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_user_update, parents=parents
    )
    u_update_parser.add_argument("user_id", help=messages.arg_help_user_update_id)
    u_update_parser.add_argument("--login", help=messages.arg_help_user_login)
    u_update_parser.add_argument(
        "--firstname", "-f", help=messages.arg_help_user_firstname
    )
    u_update_parser.add_argument(
        "--lastname", "-l", help=messages.arg_help_user_lastname
    )
    u_update_parser.add_argument("--mail", "-m", help=messages.arg_help_user_mail)
    u_update_parser.add_argument("--password", help=messages.arg_help_user_password)
    u_update_parser.add_argument(
        "--auth_source_id", type=int, help=messages.arg_help_user_auth_source_id
    )
    u_update_parser.add_argument(
        "--mail_notification",
        choices=MAIL_NOTIFICATION_CHOICES,
        help=messages.arg_help_user_mail_notification,
    )
    u_update_parser.add_argument(
        "--must_change_passwd",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=messages.arg_help_user_must_change_passwd_update,
    )
    u_update_parser.add_argument(
        "--admin",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=messages.arg_help_user_admin_update,
    )

    u_delete_parser = u_subparsers.add_parser(
        "delete", aliases=["d"], help=messages.arg_help_user_delete, parents=parents
    )
    u_delete_parser.add_argument("user_id", help=messages.arg_help_user_delete_id)
    u_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def handle_user(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.user_command)
    if cmd == "create":
        _create_user(
            login=args.login,
            firstname=args.firstname,
            lastname=args.lastname,
            mail=args.mail,
            password=args.password,
            auth_source_id=args.auth_source_id,
            mail_notification=args.mail_notification,
            must_change_passwd=args.must_change_passwd or None,
            generate_password=args.generate_password or None,
            admin=args.admin or None,
        )
        return
    if cmd == "view":
        _view_user(args.user_id, full=args.full)
        return
    if cmd == "update":
        _update_user(
            user_id=args.user_id,
            login=args.login,
            firstname=args.firstname,
            lastname=args.lastname,
            mail=args.mail,
            password=args.password,
            auth_source_id=args.auth_source_id,
            mail_notification=args.mail_notification,
            must_change_passwd=args.must_change_passwd,
            admin=args.admin,
        )
        return
    if cmd == "delete":
        if not args.yes:
            user = _read_user(args.user_id)
            summary = messages.delete_target_user.format(summary=user_summary(user))
            confirm_delete_with_identifier(
                summary, user.get("login", ""), messages.arg_help_user_login
            )
        _delete_user(args.user_id)
        return
    if cmd == "list" or cmd is None:
        _list_users(
            status=args.status,
            name=args.name,
            group_id=args.group_id,
            limit=args.limit,
            offset=args.offset,
            full=args.full,
        )
