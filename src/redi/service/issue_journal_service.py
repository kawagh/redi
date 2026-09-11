"""イシューのコメント(ジャーナル)操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とステータスコードの解釈は
`api.issue_journal` が持つ。
"""

from redi.api import issue_journal as issue_journal_api


def update_issue_journal(journal_id: str, notes: str) -> None:
    """コメントの本文を更新する。

    Raises:
        IssueJournalNotFoundException: 対象コメントが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    issue_journal_api.update_issue_journal(journal_id, notes)


def delete_issue_journal(journal_id: str) -> None:
    """コメントを削除する。

    Redmine にコメントを消す API は無いため、本文を空にすることで削除とする。

    Raises:
        IssueJournalNotFoundException: 対象コメントが存在しない (HTTP 404)
        requests.exceptions.HTTPError: それ以外の HTTP エラー
    """
    issue_journal_api.update_issue_journal(journal_id, "")
