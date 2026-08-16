"""イシュー操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は `api.issue` が持つ。
"""

from redi.api import issue as issue_api


def delete_issue(issue_id: str) -> None:
    """イシューを削除する。

    Raises:
        IssueNotFoundException: 対象イシューが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    issue_api.delete_issue(issue_id)
