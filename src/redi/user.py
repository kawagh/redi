import json

from redi.client import client


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
