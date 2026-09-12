import pytest

from redi.api.issue import IssueNotFoundException
from redi.cli import issue_guard
from redi.i18n import messages


class TestExitIfIssueNotFound:
    """exit_if_issue_not_found() はイシューが無いことを伝えて exit 1 する"""

    def test_reports_missing_issue_and_exits(self, capsys):
        """IssueNotFoundException を id 付きの issue_not_found メッセージと exit 1 に変える"""
        with (
            pytest.raises(SystemExit) as exc,
            issue_guard.exit_if_issue_not_found("42"),
        ):
            raise IssueNotFoundException("42")
        assert exc.value.code == 1
        assert messages.issue_not_found.format(id="42") in capsys.readouterr().err

    def test_passes_through_other_exceptions(self):
        """イシュー不在以外の例外は呼び出し元がそのまま受け取れる"""
        with pytest.raises(ValueError), issue_guard.exit_if_issue_not_found("42"):
            raise ValueError("other")

    def test_no_output_on_success(self, capsys):
        """例外が出なければ何も出力しない"""
        with issue_guard.exit_if_issue_not_found("42"):
            pass
        assert capsys.readouterr().err == ""


class TestReadIssueOrExit:
    """read_issue_or_exit() はイシューを取得し、無ければ exit 1 する"""

    def test_returns_issue_with_include(self, monkeypatch):
        """include を service にそのまま渡し、取得したイシューを返す"""
        called = {}

        def read_issue(issue_id, include=""):
            called["args"] = (issue_id, include)
            return {"id": 42}

        monkeypatch.setattr(issue_guard.issue_service, "read_issue", read_issue)
        issue = issue_guard.read_issue_or_exit("42", include="journals")
        assert issue == {"id": 42}
        assert called["args"] == ("42", "journals")

    def test_exits_when_issue_not_found(self, monkeypatch, capsys):
        """存在しないイシューは issue_not_found を標準エラーに出して exit 1"""

        def read_issue(issue_id, include=""):
            raise IssueNotFoundException(issue_id)

        monkeypatch.setattr(issue_guard.issue_service, "read_issue", read_issue)
        with pytest.raises(SystemExit) as exc:
            issue_guard.read_issue_or_exit("42")
        assert exc.value.code == 1
        assert messages.issue_not_found.format(id="42") in capsys.readouterr().err
