"""バージョン操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.version` が持つ。
"""

from redi import config
from redi.api import version as version_api
from redi.api.version import Version


def version_url(version_id: str | int) -> str:
    """バージョンの Web UI 上の URL を組み立てる。"""
    return f"{config.redmine_url}/versions/{version_id}"


def list_versions(project_id: str) -> list[Version]:
    """プロジェクトのバージョン一覧を取得する。"""
    return version_api.fetch_versions(project_id)


def read_version(version_id: str) -> Version:
    """バージョンを取得する。

    Raises:
        VersionNotFoundException: 対象バージョンが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return version_api.fetch_version(version_id)


def create_version(
    project_id: str,
    name: str,
    status: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
    sharing: str | None = None,
) -> Version:
    """バージョンを作成し、作成されたバージョンを返す。

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return version_api.create_version(
        project_id=project_id,
        name=name,
        status=status,
        due_date=due_date,
        description=description,
        sharing=sharing,
    )


def has_update_fields(
    name: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
    sharing: str | None = None,
) -> bool:
    """更新する項目が指定されているかを返す。

    due_date / description は空文字が値を消す指定なので、None でなければ指定ありとする。
    """
    return (
        bool(name or status or sharing)
        or due_date is not None
        or description is not None
    )


def update_version(
    version_id: str,
    name: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
    sharing: str | None = None,
) -> None:
    """バージョンを更新する。

    Raises:
        VersionNotFoundException: 対象バージョンが存在しない (HTTP 404)
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    version_api.update_version(
        version_id=version_id,
        name=name,
        status=status,
        due_date=due_date,
        description=description,
        sharing=sharing,
    )


def delete_version(version_id: str) -> None:
    """バージョンを削除する。

    Raises:
        VersionNotFoundException: 対象バージョンが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    version_api.delete_version(version_id)
