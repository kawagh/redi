from __future__ import annotations

from redi.client import client


class IssueJournalNotFoundException(Exception):
    def __init__(self, journal_id: str) -> None:
        super().__init__(journal_id)
        self.journal_id = journal_id


def update_issue_journal(journal_id: str, notes: str) -> None:
    """コメント(ジャーナル)の本文を更新する

    Raises:
        IssueJournalNotFoundException: 対象コメントが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.put(
        f"/journals/{journal_id}.json",
        json={"journal": {"notes": notes}},
    )
    if response.status_code == 404:
        raise IssueJournalNotFoundException(journal_id)
    response.raise_for_status()
