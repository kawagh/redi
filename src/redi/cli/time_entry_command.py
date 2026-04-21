import argparse

from redi.cli._common import resolve_alias
from redi.config import default_project_id
from redi.api.time_entry import (
    create_time_entry,
    delete_time_entry,
    list_time_entries,
    read_time_entry,
    update_time_entry,
)


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
    te_view_parser = te_subparsers.add_parser(
        "view", aliases=["v"], help="作業時間詳細"
    )
    te_view_parser.add_argument("time_entry_id", help="作業時間ID")
    te_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    te_update_parser = te_subparsers.add_parser(
        "update", aliases=["u"], help="作業時間更新"
    )
    te_update_parser.add_argument("time_entry_id", help="作業時間ID")
    te_update_parser.add_argument("--hours", type=float, help="時間（例: 1.5）")
    te_update_parser.add_argument("--issue_id", "-i", help="イシューID")
    te_update_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    te_update_parser.add_argument("--activity_id", "-a", help="作業分類ID")
    te_update_parser.add_argument("--spent_on", help="日付（YYYY-MM-DD）")
    te_update_parser.add_argument("--comments", "-c", help="コメント")
    te_delete_parser = te_subparsers.add_parser(
        "delete", aliases=["d"], help="作業時間削除"
    )
    te_delete_parser.add_argument("time_entry_id", help="作業時間ID")


def handle_time_entry(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.time_entry_command)
    if cmd == "create":
        project_id = args.project_id or default_project_id
        create_time_entry(
            issue_id=args.issue_id,
            project_id=project_id,
            hours=args.hours,
            activity_id=args.activity_id,
            spent_on=args.spent_on,
            comments=args.comments,
        )
    elif cmd == "view":
        read_time_entry(args.time_entry_id, full=args.full)
    elif cmd == "update":
        update_time_entry(
            time_entry_id=args.time_entry_id,
            hours=args.hours,
            issue_id=args.issue_id,
            project_id=args.project_id,
            activity_id=args.activity_id,
            spent_on=args.spent_on,
            comments=args.comments,
        )
    elif cmd == "delete":
        delete_time_entry(args.time_entry_id)
    else:
        project_id = args.project_id or default_project_id
        list_time_entries(project_id=project_id, user_id=args.user_id, full=args.full)
