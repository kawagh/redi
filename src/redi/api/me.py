from typing import NotRequired, TypedDict, cast

from redi.api.exceptions import RedmineValidationException
from redi.client import client


class MyAccount(TypedDict):
    """GET /my/account.json が返す自分のアカウント。

    `api_key` は自分のアカウントの取得時のみ返る。
    """

    id: int
    login: str
    firstname: str
    lastname: str
    mail: str
    created_on: str
    last_login_on: NotRequired[str]
    admin: NotRequired[bool]
    api_key: NotRequired[str]
    custom_fields: NotRequired[list[dict]]


def fetch_my_account() -> MyAccount:
    """自分のアカウントを取得する

    Raises:
        requests.exceptions.HTTPError: HTTP エラーが返った場合
    """
    response = client.get("/my/account.json")
    response.raise_for_status()
    return cast("MyAccount", response.json()["user"])


def update_my_account(
    firstname: str | None = None,
    lastname: str | None = None,
    mail: str | None = None,
) -> None:
    """自分のアカウントを更新する。None の項目は送らない

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 422 以外の HTTP エラーが返った場合
    """
    data: dict = {}
    if firstname is not None:
        data["firstname"] = firstname
    if lastname is not None:
        data["lastname"] = lastname
    if mail is not None:
        data["mail"] = mail
    response = client.put("/my/account.json", json={"user": data})
    if response.status_code == 422:
        raise RedmineValidationException.from_response("user", "update", response)
    response.raise_for_status()
