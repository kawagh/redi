import argparse

from redi.cli._common import confirm_delete_with_identifier, resolve_alias
from redi.i18n import messages
from redi.api.user import (
    create_user,
    delete_user,
    fetch_user,
    list_users,
    read_user,
    update_user,
)


MAIL_NOTIFICATION_CHOICES = [
    "all",
    "selected",
    "only_my_events",
    "only_assigned",
    "only_owner",
    "none",
]


def add_user_parser(subparsers: argparse._SubParsersAction) -> None:
    u_parser = subparsers.add_parser(
        "user",
        aliases=["u"],
        help=messages.arg_help_user_command,
    )
    u_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )
    u_subparsers = u_parser.add_subparsers(dest="user_command")
    u_subparsers.add_parser("list", aliases=["l"], help=messages.arg_help_user_list)
    u_create_parser = u_subparsers.add_parser(
        "create", aliases=["c"], help=messages.arg_help_user_create
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
        "view", aliases=["v"], help=messages.arg_help_user_view
    )
    u_view_parser.add_argument("user_id", help=messages.arg_help_user_view_id)
    u_view_parser.add_argument(
        "--full", action="store_true", help=messages.arg_help_full_json
    )

    u_update_parser = u_subparsers.add_parser(
        "update", aliases=["u"], help=messages.arg_help_user_update
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
        "delete", aliases=["d"], help=messages.arg_help_user_delete
    )
    u_delete_parser.add_argument("user_id", help=messages.arg_help_user_delete_id)
    u_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def handle_user(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.user_command)
    if cmd == "create":
        create_user(
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
        read_user(args.user_id, full=args.full)
        return
    if cmd == "update":
        update_user(
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
            user = fetch_user(args.user_id)
            name = f"{user.get('firstname', '')} {user.get('lastname', '')}".strip()
            summary = messages.delete_target_user.format(
                summary=f"{user['id']} {user.get('login', '')} {name}".rstrip()
            )
            confirm_delete_with_identifier(
                summary, user.get("login", ""), messages.arg_help_user_login
            )
        delete_user(args.user_id)
        return
    if cmd == "list" or cmd is None:
        list_users(full=args.full)
