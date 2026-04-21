import argparse

from redi.cli._common import resolve_alias
from redi.api.user import (
    create_user,
    delete_user,
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
        "user", aliases=["u"], help="ユーザー一覧/詳細/作成/更新/削除"
    )
    u_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    u_subparsers = u_parser.add_subparsers(dest="user_command")
    u_create_parser = u_subparsers.add_parser(
        "create", aliases=["c"], help="ユーザー作成（管理者権限が必要）"
    )
    u_create_parser.add_argument("login", help="ログイン名")
    u_create_parser.add_argument("--firstname", "-f", required=True, help="名")
    u_create_parser.add_argument("--lastname", "-l", required=True, help="姓")
    u_create_parser.add_argument("--mail", "-m", required=True, help="メールアドレス")
    u_create_parser.add_argument("--password", help="パスワード")
    u_create_parser.add_argument(
        "--generate_password",
        action="store_true",
        help="パスワードを自動生成",
    )
    u_create_parser.add_argument("--auth_source_id", type=int, help="認証ソースID")
    u_create_parser.add_argument(
        "--mail_notification",
        choices=MAIL_NOTIFICATION_CHOICES,
        help="メール通知設定",
    )
    u_create_parser.add_argument(
        "--must_change_passwd",
        action="store_true",
        help="次回ログイン時にパスワード変更を要求",
    )
    u_create_parser.add_argument(
        "--admin", action="store_true", help="管理者権限を付与"
    )

    u_view_parser = u_subparsers.add_parser("view", aliases=["v"], help="ユーザー詳細")
    u_view_parser.add_argument(
        "user_id", help="ユーザーID（'current'で現在のユーザー）"
    )
    u_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )

    u_update_parser = u_subparsers.add_parser(
        "update", aliases=["u"], help="ユーザー更新（管理者権限が必要）"
    )
    u_update_parser.add_argument("user_id", help="ユーザーID")
    u_update_parser.add_argument("--login", help="ログイン名")
    u_update_parser.add_argument("--firstname", "-f", help="名")
    u_update_parser.add_argument("--lastname", "-l", help="姓")
    u_update_parser.add_argument("--mail", "-m", help="メールアドレス")
    u_update_parser.add_argument("--password", help="パスワード")
    u_update_parser.add_argument("--auth_source_id", type=int, help="認証ソースID")
    u_update_parser.add_argument(
        "--mail_notification",
        choices=MAIL_NOTIFICATION_CHOICES,
        help="メール通知設定",
    )
    u_update_parser.add_argument(
        "--must_change_passwd",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="次回ログイン時にパスワード変更を要求 (--no-must_change_passwd で解除)",
    )
    u_update_parser.add_argument(
        "--admin",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="管理者権限 (--no-admin で解除)",
    )

    u_delete_parser = u_subparsers.add_parser(
        "delete", aliases=["d"], help="ユーザー削除（管理者権限が必要）"
    )
    u_delete_parser.add_argument("user_id", help="ユーザーID")


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
        delete_user(args.user_id)
        return
    list_users(full=args.full)
