from typing import cast

import pytest

from redi import config
from redi.api.issue import Issue
from redi.i18n import messages
from redi.service.issue_format import CLOSED_MARKER, OPEN_MARKER, format_issue_list
from redi.text_format import display_width


def make_issue(
    issue_id: int = 1,
    subject: str = "件名",
    tracker: str = "Bug",
    is_closed: bool = False,
    assignee: str | None = None,
) -> Issue:
    issue: dict = {
        "id": issue_id,
        "subject": subject,
        "tracker": {"id": 1, "name": tracker},
        "status": {"id": 1, "name": "New", "is_closed": is_closed},
    }
    if assignee is not None:
        issue["assigned_to"] = {"id": 1, "name": assignee}
    return cast(Issue, issue)


class TestColumns:
    """一覧の 1 行に triage に要る情報を並べる"""

    def test_shows_tracker_and_assignee(self):
        """id / トラッカー / 件名 / 担当者を 1 行に出す"""
        line = format_issue_list([make_issue(assignee="Admin")])[0]

        assert "#1" in line
        assert "[Bug]" in line
        assert "件名" in line
        assert "(Admin)" in line

    def test_marks_open_and_closed(self):
        """先頭マーカーで open / closed を区別する"""
        lines = format_issue_list(
            [make_issue(issue_id=1), make_issue(issue_id=2, is_closed=True)]
        )

        assert lines[0].startswith(OPEN_MARKER)
        assert lines[1].startswith(CLOSED_MARKER)

    def test_shows_unassigned_label(self):
        """担当者が居ないイシューは未担当と分かるように出す"""
        line = format_issue_list([make_issue()])[0]

        assert f"({messages.issue_list_unassigned})" in line

    def test_omits_url_by_default(self):
        """URL は 1 行の大半を占めるので既定では出さない"""
        line = format_issue_list([make_issue()])[0]

        assert "http" not in line

    def test_shows_url_when_requested(self, monkeypatch):
        """show_url=True のときだけ URL を出す"""
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")

        line = format_issue_list([make_issue()], show_url=True)[0]

        assert "http://localhost:3001/issues/1" in line

    def test_returns_no_lines_for_empty(self):
        """イシューが無いときは 1 行も出さない"""
        assert format_issue_list([]) == []


class TestAlignment:
    """列は渡したイシューの中で揃える"""

    def test_aligns_id_column(self):
        """桁数の違う id が混ざってもトラッカー以降の開始位置が揃う"""
        lines = format_issue_list([make_issue(issue_id=4), make_issue(issue_id=1234)])

        assert lines[0].index("[Bug]") == lines[1].index("[Bug]")


class TestWidth:
    """width を渡すとその表示幅に収める"""

    @pytest.mark.parametrize("width", [80, 60, 40])
    def test_truncates_subject_to_width(self, width):
        """件名を切り詰めて 1 行を width に収める(全角は 2 幅で数える)"""
        line = format_issue_list(
            [make_issue(subject="あ" * 80, assignee="Admin")], width=width
        )[0]

        assert display_width(line) <= width
        assert line.endswith("(Admin)")

    def test_keeps_subject_without_width(self):
        """width を渡さないときは件名を切り詰めない"""
        subject = "あ" * 80

        line = format_issue_list([make_issue(subject=subject)])[0]

        assert subject in line
