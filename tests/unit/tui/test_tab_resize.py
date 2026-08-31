"""端末リサイズ後の再取得 (_on_resize) の単体テスト。"""

from typing import cast

import pytest
import requests

from redi.api.issue import Issue
from redi.api.time_entry import TimeEntry
from redi.tui.issue import issue_tab
from redi.tui.state import TuiState
from redi.tui.time_entry import time_entry_tab


class TestIssueResize:
    """issue タブの _on_resize() は新しい page_size でページを取り直す"""

    def test_keeps_selected_issue_when_page_size_shrinks(self, monkeypatch):
        """page_size が縮んでも、選択していた issue が選ばれたままになる"""
        state = TuiState()
        state.page_size = 10
        state.issue_tab.offset = 0
        state.issue_tab.cursor = 15
        state.issue_tab.total_count = 60

        new_issues = [{"id": i, "subject": f"new-{i}"} for i in range(11, 21)]

        def fake_fetch(state, offset):
            # 絶対位置 15 を含むページ境界 (10) から取り直す
            assert offset == 10
            return {"issues": new_issues, "total_count": 60}

        monkeypatch.setattr(issue_tab, "fetch_issues_with_filter", fake_fetch)

        issue_tab._on_resize(state)

        assert state.issue_tab.offset == 10
        assert state.issue_tab.cursor == 5
        assert state.issue_tab.offset + state.issue_tab.cursor == 15
        assert state.issue_tab.issues == new_issues

    def test_keeps_selected_issue_when_page_size_grows(self, monkeypatch):
        """page_size が広がっても、選択していた issue が選ばれたままになる"""
        state = TuiState()
        state.page_size = 40
        state.issue_tab.offset = 20
        state.issue_tab.cursor = 3
        state.issue_tab.total_count = 60

        new_issues = [{"id": i, "subject": f"new-{i}"} for i in range(1, 41)]

        def fake_fetch(state, offset):
            assert offset == 0
            return {"issues": new_issues, "total_count": 60}

        monkeypatch.setattr(issue_tab, "fetch_issues_with_filter", fake_fetch)

        issue_tab._on_resize(state)

        assert state.issue_tab.offset == 0
        assert state.issue_tab.cursor == 23

    def test_clamps_cursor_when_fetched_page_is_shorter(self, monkeypatch):
        """取得件数が選択位置より少なければ cursor を末尾にクランプする"""
        state = TuiState()
        state.page_size = 10
        state.issue_tab.offset = 0
        state.issue_tab.cursor = 8
        state.issue_tab.total_count = 9

        monkeypatch.setattr(
            issue_tab,
            "fetch_issues_with_filter",
            lambda state, offset: {
                "issues": [{"id": 1, "subject": "only"}],
                "total_count": 1,
            },
        )

        issue_tab._on_resize(state)

        assert state.issue_tab.cursor == 0

    def test_empty_page_resets_cursor(self, monkeypatch):
        """取得結果が空でも cursor は 0 になり例外にならない"""
        state = TuiState()
        state.page_size = 10
        state.issue_tab.cursor = 5

        monkeypatch.setattr(
            issue_tab,
            "fetch_issues_with_filter",
            lambda state, offset: {"issues": [], "total_count": 0},
        )

        issue_tab._on_resize(state)

        assert state.issue_tab.issues == []
        assert state.issue_tab.cursor == 0

    def test_request_error_propagates_and_keeps_list(self, monkeypatch):
        """通信エラーは呼び出し元に伝播し、一覧は書き換えない"""
        state = TuiState()
        state.page_size = 10
        old_issues = cast(list[Issue], [{"id": 1, "subject": "old"}])
        state.issue_tab.issues = old_issues

        def fail(state, offset):
            raise requests.exceptions.ConnectionError("boom")

        monkeypatch.setattr(issue_tab, "fetch_issues_with_filter", fail)

        with pytest.raises(requests.exceptions.RequestException):
            issue_tab._on_resize(state)

        assert state.issue_tab.issues == old_issues


class TestTimeEntryResize:
    """time_entry タブの _on_resize() は新しい page_size でページを取り直す"""

    def test_keeps_selected_entry_when_page_size_shrinks(self, monkeypatch):
        """page_size が縮んでも、選択していた entry が選ばれたままになる"""
        state = TuiState()
        state.page_size = 10
        state.time_entry_tab.offset = 20
        state.time_entry_tab.cursor = 5
        state.time_entry_tab.total_count = 60

        new_entries = [{"id": i, "hours": 1.0} for i in range(21, 31)]

        def fake_fetch(state, offset):
            assert offset == 20
            return {
                "time_entries": new_entries,
                "total_count": 60,
                "issue_subjects": {1: "subject"},
            }

        monkeypatch.setattr(time_entry_tab, "_fetch_page_with_subjects", fake_fetch)

        time_entry_tab._on_resize(state)

        assert state.time_entry_tab.offset == 20
        assert state.time_entry_tab.cursor == 5
        assert state.time_entry_tab.entries == new_entries
        assert state.time_entry_tab.issue_subjects == {1: "subject"}

    def test_clamps_cursor_when_fetched_page_is_shorter(self, monkeypatch):
        """取得件数が選択位置より少なければ cursor を末尾にクランプする"""
        state = TuiState()
        state.page_size = 10
        state.time_entry_tab.offset = 0
        state.time_entry_tab.cursor = 7

        monkeypatch.setattr(
            time_entry_tab,
            "_fetch_page_with_subjects",
            lambda state, offset: {
                "time_entries": [{"id": 1, "hours": 1.0}, {"id": 2, "hours": 2.0}],
                "total_count": 2,
                "issue_subjects": {},
            },
        )

        time_entry_tab._on_resize(state)

        assert state.time_entry_tab.cursor == 1

    def test_request_error_propagates_and_keeps_list(self, monkeypatch):
        """通信エラーは呼び出し元に伝播し、一覧もエラー表示も書き換えない"""
        state = TuiState()
        state.page_size = 10
        old_entries = cast(list[TimeEntry], [{"id": 1, "hours": 1.0}])
        state.time_entry_tab.entries = old_entries

        def fail(state, offset):
            raise requests.exceptions.ConnectionError("boom")

        monkeypatch.setattr(time_entry_tab, "_fetch_page_with_subjects", fail)

        with pytest.raises(requests.exceptions.RequestException):
            time_entry_tab._on_resize(state)

        assert state.time_entry_tab.entries == old_entries
        assert state.time_entry_tab.error is None
