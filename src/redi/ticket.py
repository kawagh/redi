import requests

from redi.config import redmine_api_key, redmine_url


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
