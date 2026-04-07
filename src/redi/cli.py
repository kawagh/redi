import argparse
import os
import subprocess
import tempfile
from importlib.metadata import version

from redi.config import default_project_id, update_config
from redi.project import list_projects, read_project
from redi.ticket import add_note, list_tickets, read_ticket
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
    parser.add_argument("-V", "--version", action="version", version=f"redi {version('redi')}")
    subparsers = parser.add_subparsers(dest="command")
    p_parser = subparsers.add_parser("project", aliases=["p"], help="プロジェクト一覧/詳細")
    p_parser.add_argument("project_id", nargs="?", help="プロジェクトID")
    t_parser = subparsers.add_parser("ticket", aliases=["t"], help="チケット一覧/詳細/コメント")
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
    v_parser = subparsers.add_parser("version", aliases=["v"], help="バージョン一覧")
    v_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    w_parser = subparsers.add_parser("wiki", aliases=["w"], help="Wiki一覧/詳細")
    w_parser.add_argument("--project_id", "-p", help="プロジェクトID")
    w_parser.add_argument("page_title", nargs="?", help="Wikiページタイトル")
    c_parser = subparsers.add_parser("config", aliases=["c"], help="設定更新")
    c_parser.add_argument("--project_id", help="デフォルトプロジェクトIDを設定")
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
            list_tickets(fixed_version_id=args.version)
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
    else:
        parser.print_help()
