import requests

from redi.config import redmine_api_key, redmine_url


def list_users(project_id: str | None = None) -> None:
    if project_id:
        response = requests.get(
            f"{redmine_url}/projects/{project_id}/memberships.json",
            headers={"X-Redmine-API-Key": redmine_api_key},
        )
        response.raise_for_status()
        memberships = response.json()["memberships"]
        for m in memberships:
            if "user" in m:
                user = m["user"]
                print(f"{user['id']} {user['name']}")
    else:
        response = requests.get(
            f"{redmine_url}/users.json",
            headers={"X-Redmine-API-Key": redmine_api_key},
        )
        if response.status_code == 403:
            print("ユーザー一覧の取得には管理者権限が必要です")
            print("プロジェクトを指定してください: redi u -p <project_id>")
            return
        # 未知のステータスコードに遭遇した際にエラーをraiseする(jsonのdecodeエラーよりは原因がわかりやすい)
        response.raise_for_status()
        users = response.json()["users"]
        for user in users:
            print(f"{user['id']} {user['login']} ({user['firstname']} {user['lastname']})")
