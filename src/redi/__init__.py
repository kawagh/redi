import argparse
import os
import subprocess
import tempfile

from redi.project import list_projects, read_project
from redi.ticket import add_note, list_tickets, read_ticket
from redi.version import list_versions
from redi.wiki import list_wikis, read_wiki


def open_editor() -> str:
    # config.pyへ移動
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
    subparsers = parser.add_subparsers(dest="command")
    p_parser = subparsers.add_parser("p", help="プロジェクト一覧/詳細")
    p_parser.add_argument("project_id", nargs="?", help="プロジェクトID")
    t_parser = subparsers.add_parser("t", help="チケット一覧/詳細/コメント")
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
    v_parser = subparsers.add_parser("v", help="バージョン一覧")
    v_parser.add_argument("project_id", help="プロジェクトID")
    w_parser = subparsers.add_parser("w", help="Wiki一覧/詳細")
    # Wikiはproject_idの指定が必須
    w_parser.add_argument("project_id", help="プロジェクトID")
    w_parser.add_argument("page_title", nargs="?", help="Wikiページタイトル")
    args = parser.parse_args()

    if args.command == "p":
        if args.project_id:
            read_project(args.project_id)
        else:
            list_projects()
    elif args.command == "t":
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
    elif args.command == "v":
        list_versions(args.project_id)
    elif args.command == "w":
        if args.page_title:
            read_wiki(args.project_id, args.page_title)
        else:
            list_wikis(args.project_id)
    else:
        parser.print_help()
