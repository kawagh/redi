import argparse

from redi.cli._common import resolve_alias
from redi.config import default_project_id
from redi.api.user import create_user, list_users


def add_user_parser(subparsers: argparse._SubParsersAction) -> None:
    u_parser = subparsers.add_parser("user", aliases=["u"], help="ユーザー一覧/作成")
    u_parser.add_argument("--project_id", "-p", help="プロジェクトID")
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
        choices=[
            "all",
            "selected",
            "only_my_events",
            "only_assigned",
            "only_owner",
            "none",
        ],
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
    project_id = args.project_id or default_project_id
    list_users(project_id=project_id, full=args.full)
