import argparse
import os

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


def list_tickets() -> None:
    response = requests.get(
        f"{redmine_url}/issues.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    tickets = response.json()["issues"]
    for ticket in tickets:
        print(ticket)


def main() -> None:
    parser = argparse.ArgumentParser(description="Redmine CLI")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("p", help="プロジェクト一覧")
    subparsers.add_parser("t", help="チケット一覧")
    args = parser.parse_args()

    if args.command == "p":
        list_projects()
    elif args.command == "t":
        list_tickets()
    else:
        parser.print_help()
