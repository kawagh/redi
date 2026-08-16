"""作業時間操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.time_entry` が持つ。
"""

from redi.api import time_entry as time_entry_api


def delete_time_entry(time_entry_id: str) -> None:
    """作業時間を削除する。

    Raises:
        TimeEntryNotFoundException: 対象の作業時間が存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    time_entry_api.delete_time_entry(time_entry_id)
