import argparse

from redi.cli._common import resolve_alias
from redi.config import default_project_id
from redi.time_entry import create_time_entry, list_time_entries


def add_time_entry_parser(subparsers: argparse._SubParsersAction) -> None:
    time_entry_parser = subparsers.add_parser("time_entry", help="作業時間一覧/登録")
    time_entry_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    time_entry_parser.add_argument(
        "--user_id", "-u", help="ユーザーIDでフィルタリング（'me'も可）"
    )
    time_entry_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    te_subparsers = time_entry_parser.add_subparsers(dest="time_entry_command")
    te_create_parser = te_subparsers.add_parser(
        "create", aliases=["c"], help="作業時間登録"
    )
    te_create_parser.add_argument("hours", type=float, help="時間（例: 1.5）")
    te_create_parser.add_argument("--issue_id", "-i", help="イシューID")
    te_create_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    te_create_parser.add_argument("--activity_id", "-a", help="作業分類ID")
    te_create_parser.add_argument("--spent_on", help="日付（YYYY-MM-DD、省略で今日）")
    te_create_parser.add_argument("--comments", "-c", help="コメント")


def handle_time_entry(args: argparse.Namespace) -> None:
    if resolve_alias(args.time_entry_command) == "create":
        project_id = args.project_id or default_project_id
        create_time_entry(
            issue_id=args.issue_id,
            project_id=project_id,
            hours=args.hours,
            activity_id=args.activity_id,
            spent_on=args.spent_on,
            comments=args.comments,
        )
    else:
        project_id = args.project_id or default_project_id
        list_time_entries(project_id=project_id, user_id=args.user_id, full=args.full)
