from types import SimpleNamespace

import pytest

from redi import config
from redi.service import issue_service


@pytest.fixture
def stub_issue_api(monkeypatch):
    """コメント追加の PUT を `added` に記録し、追加後のジャーナルを `journals` で差し替える。

    コメントが Redmine に正しく届くかは E2E (`tests/e2e/test_issue_cli.py`) で見る。
    """

    state = SimpleNamespace(journals=[], added=[])

    def fake_add_note(issue_id, notes):
        state.added.append((issue_id, notes))

    def fake_fetch_issue(issue_id, include=""):
        return {"id": int(issue_id), "journals": state.journals}

    monkeypatch.setattr(issue_service.issue_api, "add_note", fake_add_note)
    monkeypatch.setattr(issue_service.issue_api, "fetch_issue", fake_fetch_issue)
    monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")
    return state


class TestAddNote:
    """add_note が返すコメントの URL"""

    def test_returns_url_with_note_number(self, stub_issue_api):
        """追加後のジャーナル数を note 番号にした URL を返す"""
        stub_issue_api.journals = [{"id": 1}, {"id": 2}]

        url = issue_service.add_note("42", "コメント")

        assert url == "http://localhost:3001/issues/42#note-2"
        assert stub_issue_api.added == [("42", "コメント")]

    def test_returns_issue_url_without_journals(self, stub_issue_api):
        """ジャーナルが取れなければ note 番号のない URL を返す"""
        url = issue_service.add_note("42", "コメント")

        assert url == "http://localhost:3001/issues/42"
