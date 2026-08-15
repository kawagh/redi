import json

import pytest

from redi import config
from redi.api import issue as issue_module

CREATED_ISSUE = {"id": 123, "subject": "件名", "project": {"id": 1, "name": "demo"}}


class FakeResponse:
    status_code = 201

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"issue": CREATED_ISSUE}


@pytest.fixture
def created_issue_response(monkeypatch):
    """create_issue の POST 先をスタブし、Redmine の URL を固定する"""
    monkeypatch.setattr(issue_module.client, "post", lambda *a, **kw: FakeResponse())
    monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")


class TestCreateIssueOutput:
    """create_issue の標準出力"""

    def test_prints_id_and_url(self, created_issue_response, capsys):
        """既定では作成した issue の id と URL を出す"""
        issue_module.create_issue(project_id="demo", subject="件名")

        out = capsys.readouterr().out
        assert "123" in out
        assert "http://localhost:3001/issues/123" in out

    def test_full_prints_json(self, created_issue_response, capsys):
        """full=True では作成した issue の JSON だけを出す"""
        issue_module.create_issue(project_id="demo", subject="件名", full=True)

        out = capsys.readouterr().out
        assert json.loads(out) == CREATED_ISSUE
