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


def list_users(project_id: str | None = None, full: bool = False) -> None:
    if project_id:
        response = client.get(f"/projects/{project_id}/memberships.json")
        response.raise_for_status()
        memberships = response.json()["memberships"]
        if full:
            print(json.dumps(memberships, ensure_ascii=False))
        else:
            for m in memberships:
                if "user" in m:
                    user = m["user"]
                    print(f"{user['id']} {user['name']}")
    else:
        response = client.get("/users.json")
        if response.status_code == 403:
            print("ユーザー一覧の取得には管理者権限が必要です")
            print("プロジェクトを指定してください: redi u -p <project_id>")
            return
        # 未知のステータスコードに遭遇した際にエラーをraiseする(jsonのdecodeエラーよりは原因がわかりやすい)
        response.raise_for_status()
        users = response.json()["users"]
        if full:
            print(json.dumps(users, ensure_ascii=False))
        else:
            for user in users:
                print(f"{user['id']} {user['login']}")
