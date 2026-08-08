import requests

from redi.api.exceptions import print_http_error_body
from redi.client import client
from redi.i18n import messages
import sys


def update_issue_journal(journal_id: str, notes: str) -> None:
    response = client.put(
        f"/journals/{journal_id}.json",
        json={"journal": {"notes": notes}},
    )
    if response.status_code == 404:
        print(messages.issue_journal_not_found.format(id=journal_id))
        sys.exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.issue_journal_update_failed)
        sys.exit(1)
    print(messages.issue_journal_updated.format(id=journal_id))


def delete_issue_journal(journal_id: str) -> None:
    response = client.put(
        f"/journals/{journal_id}.json",
        json={"journal": {"notes": ""}},
    )
    if response.status_code == 404:
        print(messages.issue_journal_not_found.format(id=journal_id))
        sys.exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.issue_journal_delete_failed)
        sys.exit(1)
    print(messages.issue_journal_deleted.format(id=journal_id))
