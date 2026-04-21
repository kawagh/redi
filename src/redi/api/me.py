import json

import requests

from redi.client import client


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
        lines.append(f"名前: {name}")
    if user.get("mail"):
        lines.append(f"メール: {user['mail']}")
    if "admin" in user:
        lines.append(f"管理者: {user['admin']}")
    if user.get("created_on"):
        lines.append(f"作成日時: {user['created_on']}")
    if user.get("last_login_on"):
        lines.append(f"最終ログイン: {user['last_login_on']}")
    custom_fields = user.get("custom_fields") or []
    if custom_fields:
        lines.append("カスタムフィールド:")
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
        print("更新内容がないので更新をキャンセルしました")
        exit(1)
    response = client.put("/my/account.json", json={"user": data})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("アカウント情報の更新に失敗しました")
        exit(1)
    print("アカウント情報を更新しました")
