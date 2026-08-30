import argparse
import sys

import requests

from redi.api.exceptions import print_http_error_body
from redi.api.issue_journal import IssueJournalNotFoundException
from redi.cli.alias import resolve_alias
from redi.cli.confirm import confirm_delete
from redi.i18n import messages
from redi.output import eprint
from redi.service import issue_journal_service


def update_issue_journal(journal_id: str, notes: str) -> None:
    """コメントを更新し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        issue_journal_service.update_issue_journal(journal_id, notes)
    except IssueJournalNotFoundException:
        eprint(messages.issue_journal_not_found.format(id=journal_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.issue_journal_update_failed)
        sys.exit(1)
    print(messages.issue_journal_updated.format(id=journal_id))


def delete_issue_journal(journal_id: str) -> None:
    """コメントを削除し、結果を標準出力に出す。失敗時は exit 1。"""
    try:
        issue_journal_service.delete_issue_journal(journal_id)
    except IssueJournalNotFoundException:
        eprint(messages.issue_journal_not_found.format(id=journal_id))
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        eprint(e)
        print_http_error_body(e)
        eprint(messages.issue_journal_delete_failed)
        sys.exit(1)
    print(messages.issue_journal_deleted.format(id=journal_id))


def add_issue_journal_parser(
    subparsers: argparse._SubParsersAction, parents: list[argparse.ArgumentParser]
) -> None:
    ij_parser = subparsers.add_parser(
        "issue_journal",
        aliases=["ij"],
        help=messages.arg_help_issue_journal_command,
        parents=parents,
    )
    ij_subparsers = ij_parser.add_subparsers(dest="issue_journal_command")
    ij_parser.set_defaults(_print_help=ij_parser.print_help)

    ij_update_parser = ij_subparsers.add_parser(
        "update",
        aliases=["u"],
        help=messages.arg_help_issue_journal_update,
        parents=parents,
    )
    ij_update_parser.add_argument(
        "journal_id", help=messages.arg_help_issue_journal_update_id
    )
    ij_update_parser.add_argument(
        "notes", help=messages.arg_help_issue_journal_update_notes
    )

    ij_delete_parser = ij_subparsers.add_parser(
        "delete",
        aliases=["d"],
        help=messages.arg_help_issue_journal_delete,
        parents=parents,
    )
    ij_delete_parser.add_argument(
        "journal_id", help=messages.arg_help_issue_journal_delete_id
    )
    ij_delete_parser.add_argument(
        "-y", "--yes", action="store_true", help=messages.arg_help_skip_confirm
    )


def handle_issue_journal(args: argparse.Namespace) -> None:
    cmd = resolve_alias(args.issue_journal_command)
    if cmd == "update":
        update_issue_journal(args.journal_id, args.notes)
        return
    if cmd == "delete":
        if not args.yes:
            confirm_delete(
                messages.delete_target_issue_journal.format(
                    id=args.journal_id, notes=""
                )
            )
        delete_issue_journal(args.journal_id)
        return
    args._print_help()
