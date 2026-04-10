# PYTHON_ARGCOMPLETE_OK
import argcomplete
import argparse
import os
import subprocess
import tempfile
from importlib.metadata import version

from redi.config import (
    default_project_id,
    editor,
    show_config,
    update_config,
    wiki_project_id,
)
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
from redi.issue import (
    add_note,
    create_issue,
    fetch_issue,
    list_issues,
    read_issue,
    update_issue,
)
from redi.tracker import list_trackers
from redi.user import list_users
from redi.version import list_versions
from redi.wiki import create_wiki, fetch_wiki, list_wikis, read_wiki, update_wiki


def open_editor(initial_text: str = "") -> str:
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", delete=False) as f:
        if initial_text:
            f.write(initial_text)
        tmp_path = f.name
    try:
        if editor == "code":
            # wait to close file
            editor_command = ["code", "--wait"]
        else:
            editor_command = [editor]

        subprocess.run([*editor_command, tmp_path], check=True)
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
    p_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    i_parser = subparsers.add_parser(
        "issue", aliases=["i"], help="イシュー一覧/詳細/作成/コメント"
    )
    i_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    i_parser.add_argument("--project_id", "-p", help="プロジェクトIDでフィルタリング")
    i_parser.add_argument(
        "--version",
        "-v",
        help="対象バージョンIDでフィルタリング",
    )
    i_parser.add_argument(
        "--assigned_to",
        "-a",
        help="担当者でフィルタリング（ユーザーIDまたは'me'）",
    )
    i_subparsers = i_parser.add_subparsers(dest="issue_command")
    i_view_parser = i_subparsers.add_parser("view", help="イシュー詳細")
    i_view_parser.add_argument("issue_id", help="イシューID")
    i_view_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    i_create_parser = i_subparsers.add_parser("create", help="イシュー作成")
    i_create_parser.add_argument("subject", help="イシューの題名")
    i_create_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    i_create_parser.add_argument("--tracker_id", "-t", help="トラッカーID")
    i_create_parser.add_argument("--priority_id", help="優先度ID")
    i_create_parser.add_argument("--assigned_to_id", "-a", help="担当者ID")
    i_update_parser = i_subparsers.add_parser("update", help="イシュー更新")
    i_update_parser.add_argument("issue_id", help="イシューID")
    i_update_parser.add_argument("--subject", "-s", help="題名")
    i_update_parser.add_argument(
        "--description",
        "-d",
        nargs="?",
        const="",
        default=None,
        help="説明（値省略でエディタ起動）",
    )
    i_update_parser.add_argument("--tracker_id", "-t", help="トラッカーID")
    i_update_parser.add_argument("--status_id", help="ステータスID")
    i_update_parser.add_argument("--priority_id", help="優先度ID")
    i_update_parser.add_argument("--assigned_to_id", "-a", help="担当者ID")
    i_update_parser.add_argument("--fixed_version_id", help="対象バージョンID")
    i_update_parser.add_argument("--notes", "-n", help="コメント")
    i_comment_parser = i_subparsers.add_parser("comment", help="イシューにコメント追加")
    i_comment_parser.add_argument("issue_id", help="イシューID")
    i_comment_parser.add_argument(
        "notes", nargs="?", default="", help="コメント（省略でエディタ起動）"
    )
    v_parser = subparsers.add_parser("version", aliases=["v"], help="バージョン一覧")
    v_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    w_parser = subparsers.add_parser("wiki", aliases=["w"], help="Wiki一覧/詳細/作成")
    w_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    w_subparsers = w_parser.add_subparsers(dest="wiki_command")
    w_view_parser = w_subparsers.add_parser("view", help="Wikiページ詳細")
    w_view_parser.add_argument("page_title", help="Wikiページタイトル")
    w_create_parser = w_subparsers.add_parser("create", help="Wikiページ作成")
    w_create_parser.add_argument("page_title", help="Wikiページタイトル")
    w_create_parser.add_argument(
        "--parent_title", required=True, help="親ページタイトル"
    )
    w_update_parser = w_subparsers.add_parser("update", help="Wikiページ更新")
    w_update_parser.add_argument("page_title", help="Wikiページタイトル")
    c_parser = subparsers.add_parser("config", aliases=["c"], help="設定更新")
    c_parser.add_argument("--project_id", help="デフォルトプロジェクトIDを設定")
    c_parser.add_argument("--wiki_project_id", help="Wiki用プロジェクトIDを設定")
    c_parser.add_argument("--editor", help="エディタを設定")
    u_parser = subparsers.add_parser("user", aliases=["u"], help="ユーザー一覧")
    u_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    u_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    tracker_parser = subparsers.add_parser("tracker", help="トラッカー一覧")
    tracker_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    issue_status_parser = subparsers.add_parser("issue_status", help="ステータス一覧")
    issue_status_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    ip_parser = subparsers.add_parser("issue_priority", help="優先度一覧")
    ip_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    tea_parser = subparsers.add_parser("time_entry_activity", help="作業分類一覧")
    tea_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    dc_parser = subparsers.add_parser("document_category", help="文書カテゴリ一覧")
    dc_parser.add_argument("--full", action="store_true", help="JSON形式で全情報を出力")
    role_parser = subparsers.add_parser("role", help="ロール一覧")
    role_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    query_parser = subparsers.add_parser("query", help="カスタムクエリ一覧")
    query_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    time_entry_parser = subparsers.add_parser("time_entry", help="作業時間一覧")
    time_entry_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    time_entry_parser.add_argument(
        "--full", action="store_true", help="JSON形式で全情報を出力"
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    if args.command in ("project", "p"):
        if args.project_id:
            read_project(args.project_id)
        else:
            list_projects(full=args.full)
    elif args.command in ("issue", "i"):
        if args.issue_command == "view":
            read_issue(args.issue_id, full=args.full)
        elif args.issue_command == "create":
            project_id = args.project_id or default_project_id
            if not project_id:
                print("project_idを指定するか、default_project_idを設定してください")
                exit(1)
            description = open_editor()
            create_issue(
                project_id=project_id,
                subject=args.subject,
                description=description,
                tracker_id=args.tracker_id,
                priority_id=args.priority_id,
                assigned_to_id=args.assigned_to_id,
            )
        elif args.issue_command == "update":
            description = args.description
            if description is not None and description == "":
                current = fetch_issue(args.issue_id)
                description = open_editor(current.get("description") or "")
            update_issue(
                issue_id=args.issue_id,
                subject=args.subject,
                description=description if description else None,
                tracker_id=args.tracker_id,
                status_id=args.status_id,
                priority_id=args.priority_id,
                assigned_to_id=args.assigned_to_id,
                fixed_version_id=args.fixed_version_id,
                notes=args.notes or "",
            )
        elif args.issue_command == "comment":
            if args.notes:
                add_note(args.issue_id, args.notes)
            else:
                notes = open_editor()
                if notes:
                    add_note(args.issue_id, notes)
                else:
                    print("コメントが空のためキャンセルしました")
        else:
            list_issues(
                project_id=args.project_id or default_project_id,
                fixed_version_id=args.version,
                assigned_to=args.assigned_to,
                full=args.full,
            )
    elif args.command in ("version", "v"):
        project_id = args.project_id or default_project_id
        if not project_id:
            print("project_idを指定するか、default_project_idを設定してください")
            exit(1)
        list_versions(project_id)
    elif args.command in ("wiki", "w"):
        project_id = args.project_id or wiki_project_id or default_project_id
        if not project_id:
            print(
                "project_idを指定するか、wiki_project_idまたはdefault_project_idを設定してください"
            )
            exit(1)
        if args.wiki_command == "view":
            read_wiki(project_id, args.page_title)
        elif args.wiki_command == "create":
            text = open_editor()
            if text:
                create_wiki(
                    project_id, args.page_title, text, parent_title=args.parent_title
                )
            else:
                print("テキストが空のためキャンセルしました")
        elif args.wiki_command == "update":
            current = fetch_wiki(project_id, args.page_title)
            text = open_editor(current.get("text") or "")
            if text:
                update_wiki(project_id, args.page_title, text)
            else:
                print("テキストが空のためキャンセルしました")
        else:
            list_wikis(project_id)
    elif args.command in ("config", "c"):
        updated = False
        if args.project_id:
            update_config("default_project_id", args.project_id)
            print(f"default_project_idを {args.project_id} に設定しました")
            updated = True
        if args.wiki_project_id:
            update_config("wiki_project_id", args.wiki_project_id)
            print(f"wiki_project_idを {args.wiki_project_id} に設定しました")
            updated = True
        if args.editor:
            update_config("editor", args.editor)
            print(f"editorを {args.editor} に設定しました")
            updated = True
        if not updated:
            show_config()
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
