import argparse

from redi.api.issue import (
    add_note,
    delete_issue,
    fetch_issue,
    list_issues,
    read_issue,
)
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.editor import open_editor
from redi.cli.issue_command.create import handle_issue_create
from redi.cli.issue_command.update import handle_issue_update
from redi.config import default_project_id
from redi.i18n import messages


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
        delete_issue(args.issue_id)
    elif cmd == "list" or cmd is None:
        list_issues(
            project_id=args.project_id or default_project_id,
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
