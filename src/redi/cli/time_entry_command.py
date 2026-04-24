import argparse

from prompt_toolkit import prompt
from prompt_toolkit.validation import Validator

from redi.cli._common import confirm_delete, inline_choice, resolve_alias
from redi.config import default_project_id
from redi.api.enumeration import fetch_time_entry_activities
from redi.api.time_entry import (
    create_time_entry,
    delete_time_entry,
    fetch_time_entry,
    list_time_entries,
    read_time_entry,
    update_time_entry,
)


def add_time_entry_parser(subparsers: argparse._SubParsersAction) -> None:
    time_entry_parser = subparsers.add_parser(
        "time_entry",
        help="list(l): 一覧, view(v): 詳細, create(c): 登録, update(u): 更新, delete(d): 削除",
    )
    time_entry_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    time_entry_parser.add_argument(
        "--user_id", "-u", help="ユーザーIDでフィルタリング（'me'も可）"
    )
    time_entry_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    te_subparsers = time_entry_parser.add_subparsers(dest="time_entry_command")
    te_subparsers.add_parser("list", aliases=["l"], help="作業時間一覧")
    te_create_parser = te_subparsers.add_parser(
        "create", aliases=["c"], help="作業時間登録"
    )
    te_create_parser.add_argument(
        "hours", type=float, nargs="?", help="時間（例: 1.5、省略で対話的に入力）"
    )
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
    te_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help="確認プロンプトをスキップ"
    )


def _interactive_fill_time_entry_create_args(args: argparse.Namespace) -> None:
    try:
        if not args.issue_id and not args.project_id:
            issue_id = prompt("イシューID（省略でプロジェクト指定に切替）: ").strip()
            if issue_id:
                args.issue_id = issue_id
            else:
                project_id = prompt(
                    "プロジェクトID または 名前/identifier: ",
                    default=default_project_id or "",
                ).strip()
                if not project_id:
                    print(
                        "イシューIDまたはプロジェクトIDが必要です。キャンセルしました"
                    )
                    exit(1)
                args.project_id = project_id
        hours_validator = Validator.from_callable(
            lambda v: v.replace(".", "", 1).isdigit(),
            error_message="数値を入力してください",
        )
        hours_str = prompt(
            "作業時間（例: 1.5 (h)）: ", validator=hours_validator
        ).strip()
        args.hours = float(hours_str)
        if not args.activity_id:
            activities = fetch_time_entry_activities()
            activity_options: list[tuple[str, str]] = [
                (str(a["id"]), a["name"]) for a in activities
            ]
            activity_labels = dict(activity_options)
            args.activity_id = inline_choice("作業分類", activity_options)
            print(f"作業分類: {activity_labels[args.activity_id]}")
        if not args.spent_on:
            args.spent_on = prompt("作業日（YYYY-MM-DD、省略で今日）: ").strip() or None
        if not args.comments:
            args.comments = prompt("コメント: ").strip() or None
    except (KeyboardInterrupt, EOFError):
        print("キャンセルしました")
        exit(1)


def handle_time_entry(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.time_entry_command)
    if cmd == "create":
        if args.hours is None:
            _interactive_fill_time_entry_create_args(args)
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
        if not args.yes:
            te = fetch_time_entry(args.time_entry_id)
            activity = (te.get("activity") or {}).get("name", "")
            confirm_delete(
                f"削除する作業時間: {te['id']} {te['hours']}h {activity} "
                f"({te['spent_on']})"
            )
        delete_time_entry(args.time_entry_id)
    elif cmd == "list" or cmd is None:
        project_id = args.project_id or default_project_id
        list_time_entries(project_id=project_id, user_id=args.user_id, full=args.full)
