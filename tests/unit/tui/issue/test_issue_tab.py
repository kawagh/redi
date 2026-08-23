from typing import cast

from redi.api.issue import Issue
from redi.tui.app_render import render_preview_current
from redi.tui.issue import issue_tab
from redi.tui.issue.issue_tab import _page_label, fetch_issues_with_filter
from redi.tui.state import IssueFilter, TuiState


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


def _make_comment_state(
    *, description_lines: int, comment_count: int, page_size: int
) -> TuiState:
    journals = [
        {
            "id": 100 + i,
            "notes": f"note {i}",
            "user": {"id": 7, "name": "me"},
            "created_on": f"2026-08-2{i}T00:00:00Z",
        }
        for i in range(comment_count)
    ]
    issue = cast(
        Issue,
        {
            "id": 1,
            "subject": "subject",
            "description": "\n".join(f"line {i}" for i in range(description_lines)),
            "journals": journals,
        },
    )
    state = TuiState()
    state.page_size = page_size
    state.me_id = "7"
    state.issue_tab.issues = [issue]
    return state


def _focused_line_in_view(state: TuiState) -> int | None:
    """右ペインの表示内容 (スクロール適用後) で、選択行が上から何行目かを返す。"""
    line = 0
    for style, text in render_preview_current(state):
        if style == "reverse":
            return line
        line += text.count("\n")
    return None


class TestCommentSelectPreviewScroll:
    """コメント選択モードでは選択中コメントが右ペインに映る"""

    def test_scrolls_into_view_on_enter(self):
        """説明が長いイシューでも、選択モードに入った時点で選択行が表示範囲に入る"""
        state = _make_comment_state(description_lines=50, comment_count=2, page_size=10)

        issue_tab.enter_comment_select_mode(state)

        line = _focused_line_in_view(state)
        assert line is not None
        assert 0 <= line < state.page_size

    def test_scrolls_into_view_on_cursor_move(self):
        """カーソルを上に動かしても選択行が表示範囲に入り続ける"""
        state = _make_comment_state(description_lines=50, comment_count=5, page_size=10)
        issue_tab.enter_comment_select_mode(state)

        issue_tab.comment_select_cursor_up(state)

        line = _focused_line_in_view(state)
        assert line is not None
        assert 0 <= line < state.page_size

    def test_keeps_scroll_when_already_visible(self):
        """選択行が既に見えているならスクロール位置は動かさない"""
        state = _make_comment_state(description_lines=2, comment_count=1, page_size=40)

        issue_tab.enter_comment_select_mode(state)

        assert state.preview_scroll == 0
