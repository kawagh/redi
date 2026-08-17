import pytest

from redi.api.issue_journal import IssueJournalNotFoundException
from redi.service import issue_journal_service


@pytest.fixture
def stub_issue_journal_api(monkeypatch):
    """コメント更新の呼び出しを記録する。

    HTTP が正しいかは E2E (`tests/e2e/test_issue_journal_cli.py`) で見る。
    """

    called: list[tuple[str, str]] = []

    def fake_update_issue_journal(journal_id, notes):
        called.append((journal_id, notes))

    monkeypatch.setattr(
        issue_journal_service.issue_journal_api,
        "update_issue_journal",
        fake_update_issue_journal,
    )
    return called


class TestUpdateIssueJournal:
    """update_issue_journal はコメントの本文を差し替える"""

    def test_passes_notes_to_api(self, stub_issue_journal_api):
        """渡された本文でコメントを更新する"""
        issue_journal_service.update_issue_journal("42", "更新後のコメント")

        assert stub_issue_journal_api == [("42", "更新後のコメント")]

    def test_propagates_not_found(self, monkeypatch):
        """存在しないコメントの例外はそのまま呼び出し元に伝える"""

        def fake_update_issue_journal(journal_id, notes):
            raise IssueJournalNotFoundException(journal_id)

        monkeypatch.setattr(
            issue_journal_service.issue_journal_api,
            "update_issue_journal",
            fake_update_issue_journal,
        )

        with pytest.raises(IssueJournalNotFoundException):
            issue_journal_service.update_issue_journal("42", "コメント")


class TestDeleteIssueJournal:
    """delete_issue_journal はコメントを削除する"""

    def test_deletes_by_emptying_notes(self, stub_issue_journal_api):
        """Redmine に削除 API が無いため本文を空にして削除とする"""
        issue_journal_service.delete_issue_journal("42")

        assert stub_issue_journal_api == [("42", "")]
