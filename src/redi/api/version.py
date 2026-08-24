from typing import NotRequired, TypedDict, cast

from redi.api.exceptions import (
    ProjectNotFoundException,
    RedmineValidationException,
)
from redi.api.types import IdName
from redi.client import client


class Version(TypedDict):
    """redmine Version

    GET /projects/{id}/versions.json / GET /versions/{id}.json を実行して
    確認できたフィールドを記載。
    未設定の due_date / wiki_page_title は省略されず null が返る。
    """

    id: int
    project: IdName
    name: str
    description: str
    # open / locked / closed
    status: str
    due_date: str | None
    # none / descendants / hierarchy / tree / system
    sharing: str
    wiki_page_title: str | None
    created_on: str
    updated_on: str
    # 個別ページ取得時のみ存在
    estimated_hours: NotRequired[float]
    spent_hours: NotRequired[float]


class VersionBody(TypedDict, total=False):
    """バージョン作成 (POST) / 更新 (PUT) のリクエストボディ。"""

    name: str
    status: str
    due_date: str
    description: str
    sharing: str


class VersionNotFoundException(Exception):
    def __init__(self, version_id: str) -> None:
        super().__init__(version_id)
        self.version_id = version_id


def _build_version_body(
    name: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
    sharing: str | None = None,
) -> VersionBody:
    """指定されたフィールドのみを持つリクエストボディを組み立てる。

    due_date / description は空文字で値を消せるよう、None でなければ送る。
    """
    body: VersionBody = {}
    if name:
        body["name"] = name
    if status:
        body["status"] = status
    if due_date is not None:
        body["due_date"] = due_date
    if description is not None:
        body["description"] = description
    if sharing:
        body["sharing"] = sharing
    return body


def fetch_versions(project_id: str) -> list[Version]:
    """プロジェクトのバージョン一覧を取得する

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.get(f"/projects/{project_id}/versions.json")
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()
    return cast("list[Version]", response.json()["versions"])


def fetch_version(version_id: str) -> Version:
    """バージョンを取得する

    Raises:
        VersionNotFoundException: 対象バージョンが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.get(f"/versions/{version_id}.json")
    if response.status_code == 404:
        raise VersionNotFoundException(version_id)
    response.raise_for_status()
    return cast("Version", response.json()["version"])


def create_version(
    project_id: str,
    name: str,
    status: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
    sharing: str | None = None,
) -> Version:
    """バージョンを作成し、作成されたバージョンを返す

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 422 以外の HTTP エラーが返った場合
    """
    body = _build_version_body(
        name=name,
        status=status,
        due_date=due_date,
        description=description,
        sharing=sharing,
    )
    response = client.post(
        f"/projects/{project_id}/versions.json", json={"version": body}
    )
    if response.status_code == 422:
        raise RedmineValidationException.from_response("version", "create", response)
    response.raise_for_status()
    return cast("Version", response.json()["version"])


def update_version(
    version_id: str,
    name: str | None = None,
    status: str | None = None,
    due_date: str | None = None,
    description: str | None = None,
    sharing: str | None = None,
) -> None:
    """バージョンを更新する

    Raises:
        VersionNotFoundException: 対象バージョンが存在しない場合（HTTP 404）
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 404 / 422 以外の HTTP エラーが返った場合
    """
    body = _build_version_body(
        name=name,
        status=status,
        due_date=due_date,
        description=description,
        sharing=sharing,
    )
    response = client.put(f"/versions/{version_id}.json", json={"version": body})
    if response.status_code == 404:
        raise VersionNotFoundException(version_id)
    if response.status_code == 422:
        raise RedmineValidationException.from_response("version", "update", response)
    response.raise_for_status()


def delete_version(version_id: str) -> None:
    """バージョンを削除する

    Raises:
        VersionNotFoundException: 対象バージョンが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.delete(f"/versions/{version_id}.json")
    if response.status_code == 404:
        raise VersionNotFoundException(version_id)
    response.raise_for_status()
