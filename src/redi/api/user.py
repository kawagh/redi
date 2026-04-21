import json

import requests

from redi.client import client
from redi.config import redmine_url


def create_user(
    login: str,
    firstname: str,
    lastname: str,
    mail: str,
    password: str | None = None,
    auth_source_id: int | None = None,
    mail_notification: str | None = None,
    must_change_passwd: bool | None = None,
    generate_password: bool | None = None,
    admin: bool | None = None,
) -> None:
    user_data: dict = {
        "login": login,
        "firstname": firstname,
        "lastname": lastname,
        "mail": mail,
    }
    if password is not None:
        user_data["password"] = password
    if auth_source_id is not None:
        user_data["auth_source_id"] = auth_source_id
    if mail_notification is not None:
        user_data["mail_notification"] = mail_notification
    if must_change_passwd is not None:
        user_data["must_change_passwd"] = must_change_passwd
    if generate_password is not None:
        user_data["generate_password"] = generate_password
    if admin is not None:
        user_data["admin"] = admin
    response = client.post("/users.json", json={"user": user_data})
    if response.status_code == 403:
        print("ユーザーの作成には管理者権限が必要です")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("ユーザーの作成に失敗しました")
        exit(1)
    created = response.json()["user"]
    print(
        f"ユーザーを作成しました: {created['id']} {created['login']} {redmine_url}/users/{created['id']}"
    )


def pop_apikey(user: dict) -> dict:
    user.pop("api_key", None)
    return user


def list_users(full: bool = False) -> None:
    response = client.get("/users.json")
    if response.status_code == 403:
        print("ユーザー一覧の取得には管理者権限が必要です")
        print(
            "プロジェクトメンバーの一覧は `redi membership -p <project_id>` を使ってください"
        )
        return
    # 未知のステータスコードに遭遇した際にエラーをraiseする(jsonのdecodeエラーよりは原因がわかりやすい)
    response.raise_for_status()
    users = [pop_apikey(u) for u in response.json()["users"]]
    if full:
        print(json.dumps(users, ensure_ascii=False))
    else:
        for user in users:
            print(f"{user['id']} {user['login']}")


def fetch_user(user_id: str, include: list[str] | None = None) -> dict:
    params = {}
    if include:
        params["include"] = ",".join(include)
    response = client.get(f"/users/{user_id}.json", params=params)
    if response.status_code == 404:
        print(f"ユーザーが見つかりません: {user_id}")
        exit(1)
    if response.status_code == 403:
        print("ユーザー詳細の取得には権限が必要です")
        exit(1)
    response.raise_for_status()
    return pop_apikey(response.json()["user"])


def read_user(user_id: str, full: bool = False) -> None:
    user = fetch_user(user_id, include=["memberships", "groups"])
    if full:
        print(json.dumps(user, ensure_ascii=False))
        return
    name = f"{user.get('firstname', '')} {user.get('lastname', '')}".strip()
    lines = [
        f"{user['id']} {user.get('login', '')} {name}".rstrip(),
        f"  メール: {user.get('mail', '')}",
    ]
    if user.get("admin"):
        lines.append("  管理者: yes")
    created_on = user.get("created_on")
    if created_on:
        lines.append(f"  作成日時: {created_on}")
    last_login_on = user.get("last_login_on")
    if last_login_on:
        lines.append(f"  最終ログイン: {last_login_on}")
    memberships = user.get("memberships") or []
    if memberships:
        lines.append("  メンバーシップ:")
        for m in memberships:
            project = m.get("project") or {}
            roles = m.get("roles") or []
            role_str = ", ".join(r.get("name", "") for r in roles)
            lines.append(
                f"    {project.get('id', '?')} {project.get('name', '')} - {role_str}"
            )
    groups = user.get("groups") or []
    if groups:
        lines.append("  グループ:")
        for g in groups:
            lines.append(f"    {g.get('id', '?')} {g.get('name', '')}")
    print("\n".join(lines))


def update_user(
    user_id: str,
    login: str | None = None,
    firstname: str | None = None,
    lastname: str | None = None,
    mail: str | None = None,
    password: str | None = None,
    auth_source_id: int | None = None,
    mail_notification: str | None = None,
    must_change_passwd: bool | None = None,
    admin: bool | None = None,
) -> None:
    data: dict = {}
    if login is not None:
        data["login"] = login
    if firstname is not None:
        data["firstname"] = firstname
    if lastname is not None:
        data["lastname"] = lastname
    if mail is not None:
        data["mail"] = mail
    if password is not None:
        data["password"] = password
    if auth_source_id is not None:
        data["auth_source_id"] = auth_source_id
    if mail_notification is not None:
        data["mail_notification"] = mail_notification
    if must_change_passwd is not None:
        data["must_change_passwd"] = must_change_passwd
    if admin is not None:
        data["admin"] = admin
    if not data:
        print("更新内容がないので更新をキャンセルしました")
        exit(1)
    response = client.put(f"/users/{user_id}.json", json={"user": data})
    if response.status_code == 404:
        print(f"ユーザーが見つかりません: {user_id}")
        exit(1)
    if response.status_code == 403:
        print("ユーザーの更新には管理者権限が必要です")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("ユーザーの更新に失敗しました")
        exit(1)
    print(f"ユーザーを更新しました: {user_id}")


def delete_user(user_id: str) -> None:
    response = client.delete(f"/users/{user_id}.json")
    if response.status_code == 404:
        print(f"ユーザーが見つかりません: {user_id}")
        exit(1)
    if response.status_code == 403:
        print("ユーザーの削除には管理者権限が必要です")
        exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("ユーザーの削除に失敗しました")
        exit(1)
    print(f"ユーザーを削除しました: {user_id}")
