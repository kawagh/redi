"""プロジェクトファイル操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.file` が持つ。
"""

from __future__ import annotations

from redi.api import file as file_api
from redi.api.attachment import upload_file
from redi.api.file import ProjectFile


def list_files(project_id: str) -> list[ProjectFile]:
    """プロジェクトのファイル一覧を取得する。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return file_api.fetch_files(project_id)


def create_file(
    project_id: str,
    file_path: str,
    version_id: int | None = None,
    description: str | None = None,
) -> str:
    """ファイルをアップロードしてプロジェクトに登録し、登録したファイル名を返す。

    Redmine ではアップロードで得た token を project files に渡す 2 段階の手順になる。

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    upload = upload_file(file_path)
    file_api.create_file(
        project_id,
        upload,
        version_id=version_id,
        description=description,
    )
    return upload["filename"]
