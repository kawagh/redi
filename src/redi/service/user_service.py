"""ユーザー操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.user` が持つ。
"""

from redi import config
from redi.api import user as user_api
from redi.api.user import User

# 詳細表示で併せて取得する情報
_DETAIL_INCLUDE = ["memberships", "groups"]

# `--status` で受け付ける値。API の数値は呼び出し元に見せない
USER_STATUS_CHOICES = list(user_api.USER_STATUS)


def user_url(user_id: str | int) -> str:
    """ユーザーの Web UI 上の URL を組み立てる。"""
    return f"{config.redmine_url}/users/{user_id}"


def pop_apikey(user: User) -> User:
    """ユーザーから API キーを取り除く。

    管理者で取得すると `api_key` が含まれるが、表示や JSON 出力には不要なため落とす。
    """
    user.pop("api_key", None)
    return user


def list_users(
    status: str | None = None,
    name: str | None = None,
    group_id: int | None = None,
    limit: int | None = None,
    offset: int | None = None,
    all_pages: bool = False,
) -> list[User]:
    """ユーザー一覧を取得する。

    既定では Redmine の一覧 API の既定件数で打ち切られる。
    取りこぼせない用途では all_pages を指定する。

    Args:
        status: `USER_STATUS_CHOICES` のいずれか。未指定なら Redmine の既定 (active のみ)
        name: login / firstname / lastname / mail への部分一致
        group_id: 所属グループ
        limit: 取得件数
        offset: 取得開始位置
        all_pages: 既定件数で打ち切らず全件取得するか

    Raises:
        UserPermissionDeniedException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    users = user_api.fetch_users(
        status=user_api.USER_STATUS[status] if status is not None else None,
        name=name,
        group_id=group_id,
        limit=limit,
        offset=offset,
        all_pages=all_pages,
    )
    return [pop_apikey(user) for user in users]


def read_user(user_id: str, detail: bool = False) -> User:
    """ユーザーを取得する。

    Args:
        detail: 所属プロジェクト・グループも併せて取得するか

    Raises:
        UserNotFoundException: 対象ユーザーが存在しない (HTTP 404)
        UserPermissionDeniedException: 参照する権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    include = _DETAIL_INCLUDE if detail else None
    return pop_apikey(user_api.fetch_user(user_id, include=include))


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
    """ユーザーを作成し、作成されたユーザーを返す。

    Raises:
        UserPermissionDeniedException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    created = user_api.create_user(
        login=login,
        firstname=firstname,
        lastname=lastname,
        mail=mail,
        password=password,
        auth_source_id=auth_source_id,
        mail_notification=mail_notification,
        must_change_passwd=must_change_passwd,
        generate_password=generate_password,
        admin=admin,
    )
    return pop_apikey(created)


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
    """ユーザーを更新する。None を渡したフィールドは更新しない。

    Raises:
        UserNotFoundException: 対象ユーザーが存在しない (HTTP 404)
        UserPermissionDeniedException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    user_api.update_user(
        user_id=user_id,
        login=login,
        firstname=firstname,
        lastname=lastname,
        mail=mail,
        password=password,
        auth_source_id=auth_source_id,
        mail_notification=mail_notification,
        must_change_passwd=must_change_passwd,
        admin=admin,
    )


def delete_user(user_id: str) -> None:
    """ユーザーを削除する。

    Raises:
        UserNotFoundException: 対象ユーザーが存在しない (HTTP 404)
        UserPermissionDeniedException: 管理者権限が無い (HTTP 403)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    user_api.delete_user(user_id)
