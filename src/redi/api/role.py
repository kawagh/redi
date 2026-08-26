from redi.client import client


def fetch_roles() -> list[dict]:
    response = client.get("/roles.json")
    response.raise_for_status()
    return response.json()["roles"]


def fetch_role(role_id: str) -> dict | None:
    """ロールを返す。存在しない場合は None を返す。"""
    response = client.get(f"/roles/{role_id}.json")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()["role"]
