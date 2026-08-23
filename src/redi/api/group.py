from typing import NotRequired, TypedDict, cast

from redi.api.types import IdName
from redi.client import client


class GroupMembership(TypedDict):
    """グループが参加しているプロジェクトと、そこで持つロール。

    GET /groups/{id}.json?include=memberships で返るフィールドを記載。
    """

    id: int
    project: IdName
    roles: list[IdName]


class Group(TypedDict):
    """redmine group

    GET /groups.json / GET /groups/{id}.json を実行して確認できたフィールドを記載。
    一覧では id / name のみが返り、users / memberships は個別取得時に
    include で指定した場合のみ含まれる。
    """

    id: int
    name: str
    # include=users 指定時のみ存在
    users: NotRequired[list[IdName]]
    # include=memberships 指定時のみ存在
    memberships: NotRequired[list[GroupMembership]]


class GroupNotFoundException(Exception):
    def __init__(self, group_id: str) -> None:
        super().__init__(group_id)
        self.group_id = group_id


class GroupUserNotFoundException(Exception):
    """グループへのユーザー追加・削除で、グループとユーザーのどちらかが存在しないときに送出する。

    Redmine はどちらが無いのかを区別せず 404 を返すため、両方を保持する。
    """

    def __init__(self, group_id: str, user_id: int) -> None:
        super().__init__(f"{group_id}/{user_id}")
        self.group_id = group_id
        self.user_id = user_id


class GroupAdminRequiredException(Exception):
    """管理者権限が無い状態で group API を呼んだときに送出する例外 (HTTP 403)。"""


def fetch_groups() -> list[Group]:
    """グループ一覧を取得する。"""
    response = client.get("/groups.json")
    response.raise_for_status()
    return cast("list[Group]", response.json()["groups"])


def fetch_group(group_id: str, include: str = "") -> Group:
    """グループを取得する。

    Args:
        include: users / memberships をカンマ区切りで指定する

    Raises:
        GroupNotFoundException: 対象グループが存在しない (HTTP 404)
        GroupAdminRequiredException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    params: dict = {}
    if include:
        params["include"] = include
    response = client.get(f"/groups/{group_id}.json", params=params)
    if response.status_code == 404:
        raise GroupNotFoundException(group_id)
    if response.status_code == 403:
        raise GroupAdminRequiredException
    response.raise_for_status()
    return cast("Group", response.json()["group"])


def create_group(name: str, user_ids: list[int] | None = None) -> Group:
    """グループを作成し、作成されたグループを返す。

    Raises:
        GroupAdminRequiredException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    group_data: dict = {"name": name}
    if user_ids:
        group_data["user_ids"] = user_ids
    response = client.post("/groups.json", json={"group": group_data})
    if response.status_code == 403:
        raise GroupAdminRequiredException
    response.raise_for_status()
    return cast("Group", response.json()["group"])


def update_group(
    group_id: str,
    name: str | None = None,
    user_ids: list[int] | None = None,
) -> None:
    """グループを更新する。None を渡した項目は変更しない。

    Raises:
        GroupNotFoundException: 対象グループが存在しない (HTTP 404)
        GroupAdminRequiredException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    data: dict = {}
    if name is not None:
        data["name"] = name
    if user_ids is not None:
        data["user_ids"] = user_ids
    response = client.put(f"/groups/{group_id}.json", json={"group": data})
    if response.status_code == 404:
        raise GroupNotFoundException(group_id)
    if response.status_code == 403:
        raise GroupAdminRequiredException
    response.raise_for_status()


def delete_group(group_id: str) -> None:
    """グループを削除する。

    Raises:
        GroupNotFoundException: 対象グループが存在しない (HTTP 404)
        GroupAdminRequiredException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    response = client.delete(f"/groups/{group_id}.json")
    if response.status_code == 404:
        raise GroupNotFoundException(group_id)
    if response.status_code == 403:
        raise GroupAdminRequiredException
    response.raise_for_status()


def add_group_user(group_id: str, user_id: int) -> None:
    """グループにユーザーを追加する。

    Raises:
        GroupNotFoundException: 対象グループが存在しない (HTTP 404)
        GroupAdminRequiredException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    response = client.post(f"/groups/{group_id}/users.json", json={"user_id": user_id})
    if response.status_code == 404:
        raise GroupNotFoundException(group_id)
    if response.status_code == 403:
        raise GroupAdminRequiredException
    response.raise_for_status()


def remove_group_user(group_id: str, user_id: int) -> None:
    """グループからユーザーを外す。

    Raises:
        GroupUserNotFoundException: グループまたはユーザーが存在しない (HTTP 404)
        GroupAdminRequiredException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    response = client.delete(f"/groups/{group_id}/users/{user_id}.json")
    if response.status_code == 404:
        raise GroupUserNotFoundException(group_id, user_id)
    if response.status_code == 403:
        raise GroupAdminRequiredException
    response.raise_for_status()
