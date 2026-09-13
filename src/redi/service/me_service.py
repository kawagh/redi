"""自分のアカウント操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.me` が持つ。
"""

import requests

from redi.api import me as me_api
from redi.api.client import CONNECTION_CHECK_TIMEOUT_SECONDS, RedmineClient
from redi.api.me import MyAccount
from redi.api.user import User
from redi.service import user_service


def read_my_account() -> MyAccount:
    """自分のアカウントを取得する。

    表示にも TUI にも不要で、漏らしたくない `api_key` は落として返す。

    Raises:
        requests.exceptions.HTTPError: HTTP エラーが返った
    """
    account = me_api.fetch_my_account()
    account.pop("api_key", None)
    return account


def read_my_user() -> User:
    """自分のユーザー情報をメンバーシップ・グループ込みで取得する。

    `/my/account.json` はメンバーシップやグループを返さないため、
    `user view current` と同じ `/users/current.json` から取得する。

    Raises:
        UserNotFoundException: 自分を参照できない (HTTP 404)
        UserPermissionDeniedException: 参照する権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return user_service.read_user("current", detail=True)


def read_my_user_id() -> str | None:
    """自分のユーザー id を取得する。取得できない場合は None を返す。

    TUI の起動時に自分の判定用として呼ぶため、取得できなくても起動は止めない。
    """
    try:
        return str(me_api.fetch_my_account()["id"])
    except requests.RequestException:
        return None


def check_connection(base_url: str, api_key: str) -> MyAccount:
    """`base_url` / `api_key` で自分のアカウントが取れるか確かめる。

    グローバルの `client` は触らないので、TUI でプロファイルを切り替える前に
    今の接続先を保ったまま切替先を確かめられる。

    Raises:
        RedmineConnectionException: 接続できない (サーバ未起動・URL 違い・タイムアウト)
        requests.exceptions.HTTPError: 接続はできたが HTTP エラーが返った (API キー違いなど)
    """
    api_client = RedmineClient(base_url, api_key)
    return me_api.fetch_my_account(api_client, timeout=CONNECTION_CHECK_TIMEOUT_SECONDS)


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
