import argparse
import os
from collections import defaultdict

import requests

redmine_url = os.environ.get("REDMINE_URL")
redmine_api_key = os.environ.get("REDMINE_API_KEY")

if not redmine_url:
    print("set REDMINE_URL")
    exit(1)
if not redmine_api_key:
    print("set REDMINE_API_KEY")
    exit(1)


def list_projects() -> None:
    response = requests.get(
        f"{redmine_url}/projects.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    projects = response.json()["projects"]
    for project in projects:
        print(project)


def read_project(project_id: str) -> None:
    response = requests.get(
        f"{redmine_url}/projects/{project_id}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    project = response.json()["project"]
    print(project)


def list_tickets() -> None:
    response = requests.get(
        f"{redmine_url}/issues.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    tickets = response.json()["issues"]
    for ticket in tickets:
        print(ticket)


def read_ticket(ticket_id: str) -> None:
    response = requests.get(
        f"{redmine_url}/issues/{ticket_id}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    ticket = response.json()["issue"]

    lines = []
    lines.append(f"{ticket['id']} {ticket['subject']}")
    if ticket.get("description"):
        lines.append("")
        lines.append(ticket["description"])

    print("\n".join(lines))


def list_wikis(project_id: str) -> None:
    response = requests.get(
        f"{redmine_url}/projects/{project_id}/wiki/index.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    pages = response.json()["wiki_pages"]

    children_map = defaultdict(list)
    for page in pages:
        parent = page.get("parent", {}).get("title") if "parent" in page else None
        children_map[parent].append(page["title"])

    def print_tree(parent: str | None, prefix: str = "") -> None:
        children = sorted(children_map.get(parent, []))
        for i, title in enumerate(children):
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}{title}")
            next_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(title, next_prefix)

    print_tree(None)


def read_wiki(project_id: str, page_title: str) -> None:
    response = requests.get(
        f"{redmine_url}/projects/{project_id}/wiki/{page_title}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    wiki = response.json()["wiki_page"]
    print(wiki)


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
