from typing import cast

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
