import argparse

from redi.config import default_project_id
from redi.user import list_users


def add_user_parser(subparsers: argparse._SubParsersAction) -> None:
    u_parser = subparsers.add_parser("user", aliases=["u"], help="ユーザー一覧")
    u_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    u_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")


def handle_user(args: argparse.Namespace) -> None:
    project_id = args.project_id or default_project_id
    list_users(project_id=project_id, full=args.full)
