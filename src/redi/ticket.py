import json

import requests

from redi.config import redmine_api_key, redmine_url


def list_tickets(
    fixed_version_id: str | None = None,
    assigned_to: str | None = None,
    full: bool = False,
) -> None:
    params = {}
    if fixed_version_id:
        params["fixed_version_id"] = fixed_version_id
    if assigned_to:
        params["assigned_to_id"] = assigned_to
    response = requests.get(
        f"{redmine_url}/issues.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
        params=params,
    )
    tickets = response.json()["issues"]
    if full:
        print(json.dumps(tickets, ensure_ascii=False))
    else:
        for ticket in tickets:
            print(f"{ticket['id']} {ticket['subject']}")


def read_ticket(ticket_id: str, full: bool = False) -> None:
    response = requests.get(
        f"{redmine_url}/issues/{ticket_id}.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    ticket = response.json()["issue"]

    if full:
        print(json.dumps(ticket, ensure_ascii=False))
    else:
        lines = []
        lines.append(f"{ticket['id']} {ticket['subject']}")
        if ticket.get("description"):
            lines.append("")
            lines.append(ticket["description"])

        print("\n".join(lines))


def add_note(ticket_id: str, notes: str) -> None:
    response = requests.put(
        f"{redmine_url}/issues/{ticket_id}.json",
        headers={
            "X-Redmine-API-Key": redmine_api_key,
            "Content-Type": "application/json",
        },
        json={"issue": {"notes": notes}},
    )
    response.raise_for_status()
    print(f"コメントを追加しました: #{ticket_id}")
