import json

import requests

from redi.client import client
from redi.i18n import messages


def read_my_account(full: bool = False) -> None:
    response = client.get("/my/account.json")
    response.raise_for_status()
    user = response.json()["user"]
    user.pop("api_key", None)
    if full:
        print(json.dumps(user, ensure_ascii=False))
        return
    lines = [f"{user['id']} {user.get('login', '')}"]
    name = " ".join(filter(None, [user.get("firstname"), user.get("lastname")]))
    if name:
        lines.append(messages.label_name.format(value=name))
    if user.get("mail"):
        lines.append(messages.label_mail.format(value=user["mail"]))
    if "admin" in user:
        lines.append(messages.label_admin.format(value=user["admin"]))
    if user.get("created_on"):
        lines.append(messages.label_created_on.format(value=user["created_on"]))
    if user.get("last_login_on"):
        lines.append(messages.label_last_login_on.format(value=user["last_login_on"]))
    custom_fields = user.get("custom_fields") or []
    if custom_fields:
        lines.append(messages.label_custom_fields_header)
        for cf in custom_fields:
            lines.append(f"  {cf.get('name')}: {cf.get('value')}")
    print("\n".join(lines))


def update_my_account(
    firstname: str | None = None,
    lastname: str | None = None,
    mail: str | None = None,
) -> None:
    data: dict = {}
    if firstname is not None:
        data["firstname"] = firstname
    if lastname is not None:
        data["lastname"] = lastname
    if mail is not None:
        data["mail"] = mail
    if not data:
        print(messages.update_canceled_no_changes)
        exit(1)
    response = client.put("/my/account.json", json={"user": data})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print(messages.account_update_failed)
        exit(1)
    print(messages.account_updated)
