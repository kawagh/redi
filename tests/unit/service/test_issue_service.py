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


@pytest.fixture
def stub_update_issue_api(monkeypatch):
    """更新の PUT を `calls` に記録し、slug -> id の解決を差し替える。

    プロジェクトの解決は `reditest` -> `5` の 1 件だけを知っている状態にする。
    """

    calls: list[dict] = []

    def fake_resolve_project_id(project_id):
        return "5" if project_id == "reditest" else project_id

    def fake_update_issue(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(issue_service, "resolve_project_id", fake_resolve_project_id)
    monkeypatch.setattr(issue_service.issue_api, "update_issue", fake_update_issue)
    return SimpleNamespace(calls=calls)


class TestUpdateIssue:
    """update_issue が API に渡す project_id"""

    def test_project_slug_is_resolved_to_id(self, stub_update_issue_api):
        """存在しない移動先を Redmine が黙って無視するので、数値の id に解決してから渡す"""
        issue_service.update_issue("42", project_id="reditest")

        assert stub_update_issue_api.calls[0]["project_id"] == "5"

    def test_project_is_not_resolved_when_omitted(self, stub_update_issue_api):
        """project_id を指定しなければ解決せず None のまま渡す (プロジェクトを変えない)"""
        issue_service.update_issue("42", subject="件名")

        assert stub_update_issue_api.calls[0]["project_id"] is None


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
