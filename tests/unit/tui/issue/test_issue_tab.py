from typing import cast

import pytest
import requests
from prompt_toolkit.utils import get_cwidth

from redi.api.issue import Issue
from redi.tui.issue import issue_tab
from redi.tui.issue.issue_tab import _page_label, fetch_issues_with_filter
from redi.tui.state import TuiState
from redi.tui.state.issue_tab import IssueFilter, IssueFind


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


class TestActionKeyResult:
    """アクションキーで TUI を抜けるときの TuiResult"""

    def test_update_carries_cursor_issue_id_as_int(self):
        """u はカーソル行のイシュー id を int のまま載せる"""
        state = _make_state(offset=0, page_size=25, total_count=3, issues_on_page=3)
        state.issue_tab.cursor = 2

        result = issue_tab.ISSUE_TAB.on_action_key(state, "u")

        assert result is not None
        assert result.action == "update"
        assert result.issue_id == 2

    def test_create_does_not_carry_issue_id(self):
        """c はカーソル行と無関係なので issue_id を載せない"""
        state = _make_state(offset=0, page_size=25, total_count=3, issues_on_page=3)
        state.issue_tab.cursor = 2

        result = issue_tab.ISSUE_TAB.on_action_key(state, "c")

        assert result is not None
        assert result.action == "create"
        assert result.issue_id is None


def _make_comment_state(
    *,
    description_lines: int,
    comment_count: int,
    page_size: int,
    notes: list[str] | None = None,
    preview_size: tuple[int, int] = (0, 0),
) -> TuiState:
    """コメント付きイシューを 1 件持つ state。`notes` は各コメントの本文 (省略時は 1 行)。"""
    journals = [
        {
            "id": 100 + i,
            "notes": notes[i] if notes else f"note {i}",
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
    state.preview_width, state.preview_height = preview_size
    return state


def _focused_block(state: TuiState) -> issue_tab.CommentBlock:
    edit = state.issue_tab.comment_select
    return issue_tab._layout_preview(state).blocks[edit.editable_indexes[edit.cursor]]


def _display_row_of(state: TuiState, line: int) -> int:
    """論理行 `line` が右ペインの上から何行目に描画されるか (折り返し込み)。

    右ペインは wrap_lines=True なので、幅を超える行は複数行を占める。
    幅が 0 のときは折り返し無し。
    """
    lines = "".join(t for _, t in issue_tab._render_preview(state)).split("\n")
    width = state.preview_width
    rows = 0
    for text in lines[state.preview_scroll : line]:
        rows += max(1, -(-get_cwidth(text) // width)) if width > 0 else 1
    return rows


def _visible_height(state: TuiState) -> int:
    return state.preview_height or state.page_size


class TestPreviewLayout:
    """右ペインの描画結果にはコメントごとの行範囲が付く"""

    def test_blocks_cover_header_and_notes(self):
        """各コメントの範囲は見出し行から本文の最終行まで"""
        state = _make_comment_state(
            description_lines=3, comment_count=2, page_size=20, notes=["a\nb", "c"]
        )
        issue_tab.enter_comment_select_mode(state)

        layout = issue_tab._layout_preview(state)
        lines = "".join(t for _, t in layout.parts).split("\n")

        first, second = layout.blocks[0], layout.blocks[1]
        assert "[2026-08-20T00:00:00Z] me" in lines[first.header_line]
        assert lines[first.last_line].strip() == "b"
        assert second.header_line == first.last_line + 1
        assert lines[second.last_line].strip() == "c"


class TestCommentSelectPreviewScroll:
    """コメント選択モードでは選択中コメントが右ペインに映る"""

    def test_scrolls_into_view_on_enter(self):
        """説明が長いイシューでも、選択モードに入った時点で選択行が表示範囲に入る"""
        state = _make_comment_state(description_lines=50, comment_count=2, page_size=10)

        issue_tab.enter_comment_select_mode(state)

        row = _display_row_of(state, _focused_block(state).header_line)
        assert 0 <= row < _visible_height(state)

    def test_scrolls_into_view_on_cursor_move(self):
        """カーソルを上に動かしても選択行が表示範囲に入り続ける"""
        state = _make_comment_state(description_lines=50, comment_count=5, page_size=10)
        issue_tab.enter_comment_select_mode(state)

        issue_tab.comment_select_cursor_up(state)

        row = _display_row_of(state, _focused_block(state).header_line)
        assert 0 <= row < _visible_height(state)

    def test_keeps_scroll_when_already_visible(self):
        """選択行が既に見えているならスクロール位置は動かさない"""
        state = _make_comment_state(description_lines=2, comment_count=1, page_size=40)

        issue_tab.enter_comment_select_mode(state)

        assert state.preview_scroll == 0

    def test_counts_wrapped_lines_when_moving_down(self):
        """長い行が折り返すコメントの下へ j で移ると、折り返し込みで見える位置まで送る"""
        # 幅 20 桁で 200 文字の本文は 10 行に折り返す。論理行では見出し同士が 2 行しか
        # 離れていないので、論理行で数えると「見えている」と誤判定して動かない。
        state = _make_comment_state(
            description_lines=2,
            comment_count=2,
            page_size=8,
            notes=["x" * 200, "short"],
            preview_size=(20, 8),
        )
        issue_tab.enter_comment_select_mode(state)
        issue_tab.comment_select_cursor_up(state)
        first_header = _focused_block(state).header_line
        assert state.preview_scroll == first_header

        issue_tab.comment_select_cursor_down(state)

        block = _focused_block(state)
        assert block.header_line - first_header < _visible_height(state)
        assert state.preview_scroll > first_header
        row = _display_row_of(state, block.header_line)
        assert 0 <= row < _visible_height(state)

    def test_moving_down_scrolls_just_enough_to_show_comment(self):
        """下に外れたときは、そのコメント全体が収まる最小の量だけ送る (先頭に飛ばさない)"""
        # 上のコメント (見出し + 12 行) が高さ 12 を超えるので、下のコメントの見出しは画面外
        notes = [
            "\n".join(f"n{i}" for i in range(12)),
            "\n".join(f"m{i}" for i in range(5)),
        ]
        state = _make_comment_state(
            description_lines=20,
            comment_count=2,
            page_size=12,
            notes=notes,
            preview_size=(0, 12),
        )
        issue_tab.enter_comment_select_mode(state)
        issue_tab.comment_select_cursor_up(state)

        issue_tab.comment_select_cursor_down(state)

        block = _focused_block(state)
        assert state.preview_scroll < block.header_line
        assert block.last_line - state.preview_scroll + 1 == _visible_height(state)

    def test_tall_comment_puts_header_on_top(self):
        """表示範囲より長いコメントに下から移ったときは見出しを先頭に置く"""
        # 上のコメントで下の見出しが画面外になり、下のコメントは高さ 10 に収まらない
        notes = [
            "\n".join(f"n{i}" for i in range(12)),
            "\n".join(f"m{i}" for i in range(20)),
        ]
        state = _make_comment_state(
            description_lines=20,
            comment_count=2,
            page_size=10,
            notes=notes,
            preview_size=(0, 10),
        )
        issue_tab.enter_comment_select_mode(state)
        issue_tab.comment_select_cursor_up(state)

        issue_tab.comment_select_cursor_down(state)

        assert state.preview_scroll == _focused_block(state).header_line
