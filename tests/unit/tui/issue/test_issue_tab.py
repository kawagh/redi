from typing import cast

import pytest
import requests

from redi.api.issue import Issue
from redi.tui.issue import issue_tab
from redi.tui.issue.issue_tab import _page_label, fetch_issues_with_filter
from redi.tui.state import IssueFilter, IssueFind, TuiState


def _make_state(
    *, offset: int, page_size: int, total_count: int, issues_on_page: int
) -> TuiState:
    state = TuiState()
    state.page_size = page_size
    state.issue_tab.offset = offset
    state.issue_tab.total_count = total_count
    state.issue_tab.issues = cast(
        list[Issue], [{"id": i, "subject": ""} for i in range(issues_on_page)]
    )
    return state


class TestPageLabel:
    """_page_label() はステータスラインに出すページ表示文字列を返す"""

    def test_first_page_full(self):
        """page_size 25, total 87 で先頭ページなら 1/4 (1-25 / 87)"""
        state = _make_state(offset=0, page_size=25, total_count=87, issues_on_page=25)
        assert _page_label(state) == "Page 1/4 (1-25 / 87)"

    def test_middle_page(self):
        """offset=25 (2ページ目) なら 2/4 (26-50 / 87)"""
        state = _make_state(offset=25, page_size=25, total_count=87, issues_on_page=25)
        assert _page_label(state) == "Page 2/4 (26-50 / 87)"

    def test_last_partial_page(self):
        """最終ページが部分埋まり (12件) なら end は total に揃う"""
        state = _make_state(offset=75, page_size=25, total_count=87, issues_on_page=12)
        assert _page_label(state) == "Page 4/4 (76-87 / 87)"

    def test_single_page_when_total_fits(self):
        """total <= page_size なら 1/1"""
        state = _make_state(offset=0, page_size=25, total_count=10, issues_on_page=10)
        assert _page_label(state) == "Page 1/1 (1-10 / 10)"

    def test_total_count_exact_multiple(self):
        """total が page_size の倍数のとき total_pages がずれない"""
        state = _make_state(offset=25, page_size=25, total_count=50, issues_on_page=25)
        assert _page_label(state) == "Page 2/2 (26-50 / 50)"

    def test_empty_state_does_not_crash(self):
        """issues が空でも例外を投げない (例: 0件のフィルタ結果)"""
        state = _make_state(offset=0, page_size=25, total_count=0, issues_on_page=0)
        assert _page_label(state) == "Page 1/1 (0 / 0)"


class TestFetchIssuesWithFilter:
    """fetch_issues_with_filter() は現在の絞り込み条件を API に渡す"""

    def test_passes_all_filter_fields(self, monkeypatch):
        """status/assignee/tracker の絞り込みをそのまま API パラメータに渡す"""
        captured = {}

        def fake_fetch_issues_page(**kwargs):
            captured.update(kwargs)
            return {"issues": [], "total_count": 0}

        monkeypatch.setattr(issue_tab, "fetch_issues_page", fake_fetch_issues_page)
        state = TuiState()
        state.page_size = 25
        state.issue_tab.filter = IssueFilter(
            status_id="closed",
            status_label="closed only",
            assigned_to_id="me",
            assigned_to_label="me",
            tracker_id="1",
            tracker_label="Bug",
        )

        fetch_issues_with_filter(state, 0)

        assert captured["status_id"] == "closed"
        assert captured["assigned_to"] == "me"
        assert captured["tracker_id"] == "1"

    def test_passes_query_id(self, monkeypatch):
        """クエリで絞り込んでいるときは query_id を API パラメータに渡す"""
        captured = {}

        def fake_fetch_issues_page(**kwargs):
            captured.update(kwargs)
            return {"issues": [], "total_count": 0}

        monkeypatch.setattr(issue_tab, "fetch_issues_page", fake_fetch_issues_page)
        state = TuiState()
        state.page_size = 25
        state.issue_tab.filter = IssueFilter(query_id="7", query_label="My open issues")

        fetch_issues_with_filter(state, 0)

        assert captured["query_id"] == "7"


class TestFetchIssuesWhileSearching:
    """検索中の fetch_issues_with_filter は検索結果を取りに行く"""

    def test_uses_search_service(self, monkeypatch):
        """検索クエリがあるときは検索 API 経由で取得し、フィルタ条件は渡さない"""
        captured = {}

        def fake_search_issues_page(**kwargs):
            captured.update(kwargs)
            return {"issues": [], "total_count": 0}

        def unexpected_fetch(**kwargs):
            raise AssertionError("検索中は通常のイシュー一覧を取りに行かない")

        monkeypatch.setattr(
            issue_tab.search_service, "search_issues_page", fake_search_issues_page
        )
        monkeypatch.setattr(issue_tab, "fetch_issues_page", unexpected_fetch)
        state = TuiState()
        state.page_size = 25
        state.project_id = "redi"
        state.issue_tab.filter = IssueFilter(status_id="closed", status_label="closed")
        state.issue_tab.find = IssueFind(query="hooks")

        fetch_issues_with_filter(state, 50)

        assert captured["query"] == "hooks"
        assert captured["project_id"] == "redi"
        assert captured["limit"] == 25
        assert captured["offset"] == 50

    def test_falls_back_to_filter_when_not_searching(self, monkeypatch):
        """検索を解除すると通常のイシュー一覧の取得に戻る"""
        captured = {}

        def fake_fetch_issues_page(**kwargs):
            captured.update(kwargs)
            return {"issues": [], "total_count": 0}

        monkeypatch.setattr(issue_tab, "fetch_issues_page", fake_fetch_issues_page)
        state = TuiState()
        state.page_size = 25
        state.issue_tab.find = IssueFind(query="")
        state.issue_tab.filter = IssueFilter(status_id="closed", status_label="closed")

        fetch_issues_with_filter(state, 0)

        assert captured["status_id"] == "closed"


class TestStatusHintWhileSearching:
    """検索中のステータス行は検索していることを示す"""

    def test_shows_find_label(self):
        """検索クエリをラベルとして出す"""
        state = _make_state(offset=0, page_size=25, total_count=3, issues_on_page=3)
        state.issue_tab.find = IssueFind(query="hooks")

        assert "[find=hooks]" in issue_tab._status_hint(state)

    def test_hides_filter_label(self):
        """検索がフィルタを置き換えるので、フィルタのラベルは出さない"""
        state = _make_state(offset=0, page_size=25, total_count=3, issues_on_page=3)
        state.issue_tab.find = IssueFind(query="hooks")
        state.issue_tab.filter = IssueFilter(status_id="closed", status_label="closed")

        assert "status=" not in issue_tab._status_hint(state)


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
