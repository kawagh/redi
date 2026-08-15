import json
from types import SimpleNamespace

import pytest

from redi import config
from redi.api import issue as issue_module

CREATED_ISSUE = {"id": 123, "subject": "件名"}


@pytest.fixture
def created_issue(monkeypatch):
    """create_issue の POST をスタブし、Redmine の URL を固定する"""
    response = SimpleNamespace(
        status_code=201,
        raise_for_status=lambda: None,
        json=lambda: {"issue": CREATED_ISSUE},
    )
    monkeypatch.setattr(issue_module.client, "post", lambda *a, **kw: response)
    monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")


class TestCreateIssueOutput:
    """create_issue の標準出力"""

    def test_prints_id_and_url(self, created_issue, capsys):
        """既定では作成した issue の id と URL を出す"""
        issue_module.create_issue(project_id="demo", subject="件名")

        out = capsys.readouterr().out
        assert "123" in out
        assert "http://localhost:3001/issues/123" in out

    def test_full_prints_json(self, created_issue, capsys):
        """full=True では作成した issue の JSON だけを出す"""
        issue_module.create_issue(project_id="demo", subject="件名", full=True)

        assert json.loads(capsys.readouterr().out) == CREATED_ISSUE
