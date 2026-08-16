import argparse
import sys

import requests

from redi import config
from redi.api.exceptions import print_http_error_body
from redi.api.issue import (
    IssueNotFoundException,
    add_note,
    fetch_issue,
    list_issues,
    read_issue,
)
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.editor import open_editor
from redi.cli.issue_command.create import handle_issue_create
from redi.cli.issue_command.update import handle_issue_update
from redi.i18n import messages
from redi.service import issue_service


def _delete_issue(issue_id: str) -> None:
    """イシューを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        issue_service.delete_issue(issue_id)
    except IssueNotFoundException:
        print(messages.issue_not_found.format(id=issue_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.issue_delete_failed)
        sys.exit(1)
    print(messages.issue_deleted.format(id=issue_id))


def handle_issue(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.issue_command)
    if cmd == "view":
        read_issue(
            args.issue_id,
            include=args.include or "",
            full=args.full,
            web=args.web,
        )
    elif cmd == "create":
        handle_issue_create(args)
    elif cmd == "update":
        handle_issue_update(args)
    elif cmd == "comment":
        if args.notes:
            add_note(args.issue_id, args.notes)
        else:
            notes = open_editor()
            if notes:
                add_note(args.issue_id, notes)
            else:
                print(messages.canceled_empty_comment)
    elif cmd == "delete":
        if not args.yes:
            issue = fetch_issue(args.issue_id)
            confirm_delete(
                messages.delete_target_issue.format(
                    id=issue["id"], subject=issue["subject"]
                )
            )
        _delete_issue(args.issue_id)
    elif cmd == "list" or cmd is None:
        list_issues(
            project_id=args.project_id or config.default_project_id,
            fixed_version_id=args.version,
            assigned_to=args.assigned_to,
            status_id=args.status_id,
            tracker_id=args.tracker_id,
            priority_id=args.priority_id,
            query_id=args.query_id,
            limit=args.limit,
            offset=args.offset,
            full=args.full,
        )
