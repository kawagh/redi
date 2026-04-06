import argparse

from redi.project import list_projects, read_project
from redi.ticket import list_tickets, read_ticket
from redi.wiki import list_wikis, read_wiki


def main() -> None:
    parser = argparse.ArgumentParser(description="Redmine CLI")
    subparsers = parser.add_subparsers(dest="command")
    p_parser = subparsers.add_parser("p", help="プロジェクト一覧/詳細")
    p_parser.add_argument("project_id", nargs="?", help="プロジェクトID")
    t_parser = subparsers.add_parser("t", help="チケット一覧/詳細")
    t_parser.add_argument("ticket_id", nargs="?", help="チケットID")
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
        if args.ticket_id:
            read_ticket(args.ticket_id)
        else:
            list_tickets()
    elif args.command == "w":
        if args.page_title:
            read_wiki(args.project_id, args.page_title)
        else:
            list_wikis(args.project_id)
    else:
        parser.print_help()
