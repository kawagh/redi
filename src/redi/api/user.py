from __future__ import annotations

from typing import NotRequired, TypedDict, cast

from redi.api.types import IdName
from redi.client import client


class UserMembership(TypedDict):
    """ユーザーのプロジェクト参加情報。include=memberships 指定時のみ返る。"""

    id: int
    project: IdName
    roles: list[IdName]


class User(TypedDict):
    """redmine user

    GET /users.json / GET /users/{id}.json を実行して確認できたフィールドを記載。
    mail / admin / last_login_on は自分自身か管理者で取得したときのみ返る。
    api_key は管理者で取得したときのみ返る。
    """

    id: int
    login: str
    firstname: str
    lastname: str
    created_on: str
    mail: NotRequired[str]
    admin: NotRequired[bool]
    last_login_on: NotRequired[str]
    api_key: NotRequired[str]
    # include 指定時のみ存在
    memberships: NotRequired[list[UserMembership]]
    groups: NotRequired[list[IdName]]


# GET /users.json の status パラメータ。Redmine が定める数値との対応。
USER_STATUS: dict[str, int] = {"active": 1, "registered": 2, "locked": 3}

# 一覧を1回のリクエストで取る件数 (Redmine の上限は 100)
USERS_PAGE_LIMIT = 100


class UserNotFoundException(Exception):
    def __init__(self, user_id: str) -> None:
        super().__init__(user_id)
        self.user_id = user_id


class UserPermissionDeniedException(Exception):
    """権限が不足している操作を実行したときに送出する例外（HTTP 403）。

    Redmine はユーザーの一覧取得や作成・更新・削除に管理者権限を要求し、
    不足を 403 で返す。どの操作で不足したかは呼び出し元が知っているため、
    ここでは操作を区別せず、メッセージの出し分けは呼び出し元に任せる。
    """


def fetch_users(
    status: int | None = None,
    name: str | None = None,
    group_id: int | None = None,
) -> list[User]:
    """条件に合うユーザーを全件取得する

    Redmine の一覧 API は limit 未指定だと既定件数しか返さないため、
    `total_count` を見て全件揃うまで offset を進める。

    Args:
        status: `USER_STATUS` の数値。未指定なら Redmine の既定 (active のみ)
        name: login / firstname / lastname / mail への部分一致
        group_id: 所属グループ

    Raises:
        UserPermissionDeniedException: 管理者権限が無い場合（HTTP 403）
        requests.exceptions.HTTPError: 403 以外の HTTP エラーが返った場合
    """
    filters: dict = {}
    if status is not None:
        filters["status"] = status
    if name is not None:
        filters["name"] = name
    if group_id is not None:
        filters["group_id"] = group_id
    users: list[User] = []
    offset = 0
    while True:
        response = client.get(
            "/users.json",
            params={**filters, "limit": USERS_PAGE_LIMIT, "offset": offset},
        )
        if response.status_code == 403:
            raise UserPermissionDeniedException
        # 未知のステータスコードに遭遇した際にエラーをraiseする(jsonのdecodeエラーよりは原因がわかりやすい)
        response.raise_for_status()
        data = response.json()
        page = cast("list[User]", data.get("users", []))
        users.extend(page)
        total_count = data.get("total_count")
        if not page or total_count is None or len(users) >= total_count:
            return users
        offset += len(page)


def fetch_user(user_id: str, include: list[str] | None = None) -> User:
    """ユーザーを取得する

    Raises:
        UserNotFoundException: 対象ユーザーが存在しない場合（HTTP 404）
        UserPermissionDeniedException: 参照する権限が無い場合（HTTP 403）
        requests.exceptions.HTTPError: 403 / 404 以外の HTTP エラーが返った場合
    """
    params = {}
    if include:
        params["include"] = ",".join(include)
    response = client.get(f"/users/{user_id}.json", params=params)
    if response.status_code == 404:
        raise UserNotFoundException(user_id)
    if response.status_code == 403:
        raise UserPermissionDeniedException
    response.raise_for_status()
    return cast("User", response.json()["user"])


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
) -> User:
    """ユーザーを作成し、作成されたユーザーを返す

    Raises:
        UserPermissionDeniedException: 管理者権限が無い場合（HTTP 403）
        requests.exceptions.HTTPError: 403 以外の HTTP エラーが返った場合
    """
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
        raise UserPermissionDeniedException
    response.raise_for_status()
    return cast("User", response.json()["user"])


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
    """ユーザーを更新する

    None を渡したフィールドはリクエストに含めない。

    Raises:
        UserNotFoundException: 対象ユーザーが存在しない場合（HTTP 404）
        UserPermissionDeniedException: 管理者権限が無い場合（HTTP 403）
        requests.exceptions.HTTPError: 403 / 404 以外の HTTP エラーが返った場合
    """
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
    response = client.put(f"/users/{user_id}.json", json={"user": data})
    if response.status_code == 404:
        raise UserNotFoundException(user_id)
    if response.status_code == 403:
        raise UserPermissionDeniedException
    response.raise_for_status()


def delete_user(user_id: str) -> None:
    """ユーザーを削除する

    Raises:
        UserNotFoundException: 対象ユーザーが存在しない場合（HTTP 404）
        UserPermissionDeniedException: 管理者権限が無い場合（HTTP 403）
        requests.exceptions.HTTPError: 403 / 404 以外の HTTP エラーが返った場合
    """
    response = client.delete(f"/users/{user_id}.json")
    if response.status_code == 404:
        raise UserNotFoundException(user_id)
    if response.status_code == 403:
        raise UserPermissionDeniedException
    response.raise_for_status()
