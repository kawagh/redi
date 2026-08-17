"""グループ操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.group` が持つ。
"""

from __future__ import annotations

from redi import config
from redi.api import group as group_api
from redi.api.group import Group


def group_url(group_id: int | str) -> str:
    """グループの Web UI 上の URL を組み立てる。"""
    return f"{config.redmine_url}/groups/{group_id}"


def list_groups() -> list[Group]:
    """グループ一覧を取得する。"""
    return group_api.fetch_groups()


def read_group(group_id: str, include: str = "") -> Group:
    """グループを取得する。

    Raises:
        GroupNotFoundException: 対象グループが存在しない (HTTP 404)
        GroupAdminRequiredException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return group_api.fetch_group(group_id, include=include)


def create_group(name: str, user_ids: list[int] | None = None) -> Group:
    """グループを作成し、作成されたグループを返す。

    Raises:
        GroupAdminRequiredException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return group_api.create_group(name, user_ids=user_ids)


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
    group_api.update_group(group_id, name=name, user_ids=user_ids)


def delete_group(group_id: str) -> None:
    """グループを削除する。

    Raises:
        GroupNotFoundException: 対象グループが存在しない (HTTP 404)
        GroupAdminRequiredException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    group_api.delete_group(group_id)


def add_group_user(group_id: str, user_id: int) -> None:
    """グループにユーザーを追加する。

    Raises:
        GroupNotFoundException: 対象グループが存在しない (HTTP 404)
        GroupAdminRequiredException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    group_api.add_group_user(group_id, user_id)


def remove_group_user(group_id: str, user_id: int) -> None:
    """グループからユーザーを外す。

    Raises:
        GroupUserNotFoundException: グループまたはユーザーが存在しない (HTTP 404)
        GroupAdminRequiredException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    group_api.remove_group_user(group_id, user_id)
