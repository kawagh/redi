"""自分のアカウント操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.me` が持つ。
"""

from __future__ import annotations

import requests

from redi.api import me as me_api
from redi.api.me import MyAccount


def read_my_account() -> MyAccount:
    """自分のアカウントを取得する。

    表示にも TUI にも不要で、漏らしたくない `api_key` は落として返す。

    Raises:
        requests.exceptions.HTTPError: HTTP エラーが返った
    """
    account = me_api.fetch_my_account()
    account.pop("api_key", None)
    return account


def read_my_user_id() -> str | None:
    """自分のユーザー id を取得する。取得できない場合は None を返す。

    TUI の起動時に自分の判定用として呼ぶため、取得できなくても起動は止めない。
    """
    try:
        return str(me_api.fetch_my_account()["id"])
    except requests.RequestException:
        return None


def update_my_account(
    firstname: str | None = None,
    lastname: str | None = None,
    mail: str | None = None,
) -> None:
    """自分のアカウントを更新する。

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    me_api.update_my_account(firstname=firstname, lastname=lastname, mail=mail)
