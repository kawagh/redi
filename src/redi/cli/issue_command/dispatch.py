import argparse
import sys

import requests

from redi import config
from redi.api.exceptions import print_http_error_body
from redi.api.issue import IssueNotFoundException
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.cli.editor import open_editor
from redi.cli.issue_command.create import handle_issue_create
from redi.cli.issue_command.filters import validate_list_filters
from redi.cli.issue_command.update import handle_issue_update
from redi.cli.issue_command.view import list_issues, view_issue
from redi.i18n import messages
from redi.output import eprint
from redi.service import issue_service


def add_issue_note(issue_id: str, notes: str) -> None:
    """イシューにコメントを追加し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        url = issue_service.add_note(issue_id, notes)
    except IssueNotFoundException:
        eprint(messages.issue_not_found.format(id=issue_id))
        sys.exit(1)
    print(messages.comment_added.format(url=url))


def _delete_issue(issue_id: str) -> None:
    """イシューを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        issue_service.delete_issue(issue_id)
    except IssueNotFoundException:
        eprint(messages.issue_not_found.format(id=issue_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.issue_delete_failed)
        sys.exit(1)
    print(messages.issue_deleted.format(id=issue_id))


# `--query_id` を渡すと Redmine はカスタムクエリの条件を優先し、同時に渡した条件を
# 黙って捨てる。併用が効く `--project_id` だけは対象にしない。
_QUERY_ID_CONFLICTING_FILTERS = (
    ("--version", "version"),
    ("--assigned_to", "assigned_to"),
    ("--status_id", "status_id"),
    ("--tracker_id", "tracker_id"),
    ("--priority_id", "priority_id"),
)


def _validate_query_id_filters(args: argparse.Namespace) -> None:
    """`--query_id` と併用しても無視されるフィルタがあれば、名前を示して exit 1。"""
    if not args.query_id:
        return
    ignored = [
        option
        for option, dest in _QUERY_ID_CONFLICTING_FILTERS
        if getattr(args, dest, None)
    ]
    if not ignored:
        return
    eprint(messages.error_query_id_conflicts_filters.format(options=", ".join(ignored)))
    sys.exit(1)


def handle_issue(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.issue_command)
    if cmd == "view":
        view_issue(
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
            add_issue_note(args.issue_id, args.notes)
        else:
            notes = open_editor(name="issue_note")
            if notes:
                add_issue_note(args.issue_id, notes)
            else:
                print(messages.canceled_empty_comment)
    elif cmd == "delete":
        if not args.yes:
            try:
                issue = issue_service.read_issue(args.issue_id)
            except IssueNotFoundException:
                eprint(messages.issue_not_found.format(id=args.issue_id))
                sys.exit(1)
            confirm_delete(
                messages.delete_target_issue.format(
                    id=issue["id"], subject=issue["subject"]
                )
            )
        _delete_issue(args.issue_id)
    elif cmd == "list" or cmd is None:
        _validate_query_id_filters(args)
        validate_list_filters(args)
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
