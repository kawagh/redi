import argparse
import os
import subprocess
import tempfile
from importlib.metadata import version

from redi.config import default_project_id, update_config
from redi.enumeration import (
    list_document_categories,
    list_issue_priorities,
    list_time_entry_activities,
)
from redi.issue_status import list_issue_statuses
from redi.project import list_projects, read_project
from redi.query import list_queries
from redi.role import list_roles
from redi.time_entry import list_time_entries
from redi.ticket import add_note, list_tickets, read_ticket
from redi.tracker import list_trackers
from redi.user import list_users
from redi.version import list_versions
from redi.wiki import list_wikis, read_wiki


def open_editor() -> str:
    editor = os.environ.get("REDI_EDITOR", "nvim")
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", delete=False) as f:
        tmp_path = f.name
    try:
        subprocess.run([editor, tmp_path], check=True)
        with open(tmp_path) as f:
            return f.read().strip()
    finally:
        os.unlink(tmp_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Redmine CLI")
    parser.add_argument(
        "-V", "--version", action="version", version=f"redi {version('redi')}"
    )
    subparsers = parser.add_subparsers(dest="command")
    p_parser = subparsers.add_parser(
        "project", aliases=["p"], help="プロジェクト一覧/詳細"
    )
    p_parser.add_argument("project_id", nargs="?", help="プロジェクトID")
    t_parser = subparsers.add_parser(
        "ticket", aliases=["t"], help="チケット一覧/詳細/コメント"
    )
    t_parser.add_argument("ticket_id", nargs="?", help="チケットID")
    t_parser.add_argument(
        "--notes",
        nargs="?",
        const="",
        default=None,
        help="チケットにコメントを追加（値省略でエディタ起動）",
    )
    t_parser.add_argument(
        "--version",
        "-v",
        help="対象バージョンIDでフィルタリング",
    )
    t_parser.add_argument(
        "--assigned_to",
        "-a",
        help="担当者でフィルタリング（ユーザーIDまたは'me'）",
    )
    v_parser = subparsers.add_parser("version", aliases=["v"], help="バージョン一覧")
    v_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    w_parser = subparsers.add_parser("wiki", aliases=["w"], help="Wiki一覧/詳細")
    w_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    w_parser.add_argument("page_title", nargs="?", help="Wikiページタイトル")
    c_parser = subparsers.add_parser("config", aliases=["c"], help="設定更新")
    c_parser.add_argument("--project_id", help="デフォルトプロジェクトIDを設定")
    u_parser = subparsers.add_parser("user", aliases=["u"], help="ユーザー一覧")
    u_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    u_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    tracker_parser = subparsers.add_parser("tracker", help="トラッカー一覧")
    tracker_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    issue_status_parser = subparsers.add_parser("issue_status", help="ステータス一覧")
    issue_status_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    ip_parser = subparsers.add_parser("issue_priority", help="優先度一覧")
    ip_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    tea_parser = subparsers.add_parser("time_entry_activity", help="作業分類一覧")
    tea_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    dc_parser = subparsers.add_parser("document_category", help="文書カテゴリ一覧")
    dc_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    role_parser = subparsers.add_parser("role", help="ロール一覧")
    role_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    query_parser = subparsers.add_parser("query", help="カスタムクエリ一覧")
    query_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    time_entry_parser = subparsers.add_parser("time_entry", help="作業時間一覧")
    time_entry_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    time_entry_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    args = parser.parse_args()

    if args.command in ("project", "p"):
        if args.project_id:
            read_project(args.project_id)
        else:
            list_projects()
    elif args.command in ("ticket", "t"):
        if args.ticket_id and args.notes is not None:
            if args.notes:
                add_note(args.ticket_id, args.notes)
            else:
                notes = open_editor()
                if notes:
                    add_note(args.ticket_id, notes)
                else:
                    print("コメントが空のためキャンセルしました")
        elif args.ticket_id:
            read_ticket(args.ticket_id)
        else:
            list_tickets(fixed_version_id=args.version, assigned_to=args.assigned_to)
    elif args.command in ("version", "v"):
        project_id = args.project_id or default_project_id
        if not project_id:
            print("project_idを指定するか、default_project_idを設定してください")
            exit(1)
        list_versions(project_id)
    elif args.command in ("wiki", "w"):
        project_id = args.project_id or default_project_id
        if not project_id:
            print("project_idを指定するか、default_project_idを設定してください")
            exit(1)
        if args.page_title:
            read_wiki(project_id, args.page_title)
        else:
            list_wikis(project_id)
    elif args.command in ("config", "c"):
        if args.project_id:
            update_config("default_project_id", args.project_id)
            print(f"default_project_idを {args.project_id} に設定しました")
        else:
            print("更新する設定を指定してください (例: --project_id)")
    elif args.command in ("user", "u"):
        project_id = args.project_id or default_project_id
        list_users(project_id=project_id, full=args.full)
    elif args.command == "tracker":
        list_trackers(full=args.full)
    elif args.command == "issue_status":
        list_issue_statuses(full=args.full)
    elif args.command == "issue_priority":
        list_issue_priorities(full=args.full)
    elif args.command == "time_entry_activity":
        list_time_entry_activities(full=args.full)
    elif args.command == "document_category":
        list_document_categories(full=args.full)
    elif args.command == "role":
        list_roles(full=args.full)
    elif args.command == "query":
        list_queries(full=args.full)
    elif args.command == "time_entry":
        project_id = args.project_id or default_project_id
        list_time_entries(project_id=project_id, full=args.full)
    else:
        parser.print_help()
