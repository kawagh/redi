from typing import NotRequired, TypedDict, cast

from redi.api.exceptions import ProjectNotFoundException
from redi.api.types import IdName
from redi.client import client


class ProjectFile(TypedDict):
    """プロジェクトのファイル。

    GET /projects/{id}/files.json を実行して確認できたフィールドを記載。
    """

    id: int
    filename: str
    filesize: int  # bytes
    content_type: str  # ex. text/plain
    description: str
    content_url: str
    author: IdName
    created_on: str
    digest: NotRequired[str]
    downloads: NotRequired[int]
    # バージョンに紐づけて登録した場合のみ存在
    version: NotRequired[IdName]


class ProjectFileBody(TypedDict):
    """プロジェクトファイル登録 (POST) のリクエストボディ。"""

    token: str
    filename: str
    content_type: str
    version_id: NotRequired[int]
    description: NotRequired[str]


def fetch_files(project_id: str) -> list[ProjectFile]:
    """プロジェクトのファイル一覧を取得する

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.get(f"/projects/{project_id}/files.json")
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()
    return cast("list[ProjectFile]", response.json()["files"])


def create_file(
    project_id: str,
    upload: dict,
    version_id: int | None = None,
    description: str | None = None,
) -> None:
    """アップロード済みのファイルをプロジェクトのファイルとして登録する

    Args:
        upload: アップロード結果 (`api.attachment.upload_file` の戻り値)

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    body: ProjectFileBody = {
        "token": upload["token"],
        "filename": upload["filename"],
        "content_type": upload["content_type"],
    }
    if version_id is not None:
        body["version_id"] = version_id
    if description is not None:
        body["description"] = description
    response = client.post(f"/projects/{project_id}/files.json", json={"file": body})
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()
