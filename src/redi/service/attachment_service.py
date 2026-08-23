"""添付ファイル操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は
`api.attachment` が持つ。
"""

import os
from pathlib import Path

from redi import config
from redi.api import attachment as attachment_api
from redi.api.attachment import AttachmentNotFoundException
from redi.api.types import Attachment


class LocalFileNotFoundException(Exception):
    """アップロード対象のローカルファイルが無いときに送出する例外。"""

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.path = path


class UnexpectedContentUrlException(Exception):
    """`content_url` が Redmine のホスト配下でないときに送出する例外。"""

    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.url = url


def attachment_url(attachment_id: str) -> str:
    """添付ファイルの Web UI 上の URL を組み立てる。"""
    return f"{config.redmine_url}/attachments/{attachment_id}"


def upload_file(file_path: str) -> dict:
    """ローカルファイルをアップロードし、token を含むアップロード結果を返す。

    Raises:
        LocalFileNotFoundException: `file_path` がファイルとして存在しない
        requests.exceptions.HTTPError: HTTP エラー
    """
    if not os.path.isfile(file_path):
        raise LocalFileNotFoundException(file_path)
    return attachment_api.upload_file(file_path)


def read_attachment(attachment_id: str) -> Attachment:
    """添付ファイルのメタ情報を取得する。

    Raises:
        AttachmentNotFoundException: 対象が存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    return attachment_api.fetch_attachment(attachment_id)


def resolve_download_path(attachment: Attachment, output: str | None) -> Path:
    """保存先のパスを決める。

    `output` 未指定ならカレントディレクトリに添付ファイル名で保存する。
    ディレクトリを指定した場合はその配下に添付ファイル名で保存する。
    """
    filename = Path(attachment["filename"]).name or str(attachment["id"])
    if output is None:
        return Path(filename)
    path = Path(output).expanduser()
    if path.is_dir():
        return path / filename
    return path


def resolve_download_url_path(attachment: Attachment) -> str:
    """`content_url` を Redmine のホストからの相対パスに変換する。

    Raises:
        UnexpectedContentUrlException: `content_url` が `config.redmine_url` 配下でない
    """
    # API キーを他ホストへ送らないよう、config.redmine_url 配下でない content_url は使わない
    content_url = attachment.get("content_url") or ""
    if not config.redmine_url or not content_url.startswith(config.redmine_url):
        raise UnexpectedContentUrlException(content_url)
    return content_url[len(config.redmine_url) :]


def download_attachment(attachment: Attachment, path: Path) -> None:
    """添付ファイルの実体をダウンロードして `path` に書き込む。

    Raises:
        UnexpectedContentUrlException: `content_url` が `config.redmine_url` 配下でない
        AttachmentNotFoundException: 実体が存在しない (HTTP 404)
        OSError: `path` に書き込めない
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    chunks = attachment_api.iter_attachment_content(
        resolve_download_url_path(attachment)
    )
    if chunks is None:
        raise AttachmentNotFoundException(str(attachment["id"]))
    with open(path, "wb") as f:
        # writelines() でも等価だが、チャンク単位の書き込みは for の方が可読性が高い
        for chunk in chunks:  # noqa: FURB122
            f.write(chunk)


def update_attachment(
    attachment_id: str,
    filename: str | None = None,
    description: str | None = None,
) -> None:
    """添付ファイルのファイル名・説明を更新する。

    Raises:
        AttachmentNotFoundException: 対象が存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    attachment_api.update_attachment(
        attachment_id, filename=filename, description=description
    )


def delete_attachment(attachment_id: str) -> None:
    """添付ファイルを削除する。

    Raises:
        AttachmentNotFoundException: 対象が存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    attachment_api.delete_attachment(attachment_id)
