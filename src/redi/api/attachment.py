import mimetypes
import os
from collections.abc import Iterator

from redi.api.types import Attachment
from redi.client import client

DOWNLOAD_CHUNK_SIZE = 1024 * 1024


class AttachmentNotFoundException(Exception):
    """対象の添付ファイルが存在しないときに送出する例外。"""

    def __init__(self, attachment_id: str) -> None:
        super().__init__(attachment_id)
        self.attachment_id = attachment_id


def upload_file(file_path: str) -> dict:
    """ローカルファイルをアップロードし、token を含むアップロード結果を返す。

    戻り値は issue / file の作成・更新時に `uploads` として渡す形。

    Raises:
        OSError: `file_path` を開けない
        requests.exceptions.HTTPError: HTTP エラー
    """
    filename = os.path.basename(file_path)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(file_path, "rb") as f:
        response = client.post(
            "/uploads.json",
            headers={"Content-Type": "application/octet-stream"},
            data=f,
        )
    response.raise_for_status()
    return {
        "token": response.json()["upload"]["token"],
        "filename": filename,
        "content_type": content_type,
    }


def fetch_attachment(attachment_id: str) -> Attachment:
    """添付ファイルのメタ情報を取得する。

    Raises:
        AttachmentNotFoundException: 対象が存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    response = client.get(f"/attachments/{attachment_id}.json")
    if response.status_code == 404:
        raise AttachmentNotFoundException(attachment_id)
    response.raise_for_status()
    return response.json()["attachment"]


def iter_attachment_content(url_path: str) -> Iterator[bytes] | None:
    """添付ファイルの実体をチャンク単位で読み出す。存在しない場合は None を返す。

    Args:
        url_path: Redmine のホストからの相対パス

    Raises:
        requests.exceptions.HTTPError: 404 以外の HTTP エラー
    """
    response = client.get(url_path, stream=True)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE)


def update_attachment(
    attachment_id: str,
    filename: str | None = None,
    description: str | None = None,
) -> None:
    """添付ファイルのファイル名・説明を更新する。None の項目は変更しない。

    Raises:
        AttachmentNotFoundException: 対象が存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    data: dict = {}
    if filename is not None:
        data["filename"] = filename
    if description is not None:
        data["description"] = description
    response = client.patch(
        f"/attachments/{attachment_id}.json", json={"attachment": data}
    )
    if response.status_code == 404:
        raise AttachmentNotFoundException(attachment_id)
    response.raise_for_status()


def delete_attachment(attachment_id: str) -> None:
    """添付ファイルを削除する。

    Raises:
        AttachmentNotFoundException: 対象が存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    response = client.delete(f"/attachments/{attachment_id}.json")
    if response.status_code == 404:
        raise AttachmentNotFoundException(attachment_id)
    response.raise_for_status()
