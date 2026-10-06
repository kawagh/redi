from typing import cast

import pytest
import requests

from redi.api.time_entry import TimeEntry, TimeEntryNotFoundException
from redi.i18n import messages
from redi.tui.state import TuiState
from redi.tui.time_entry import time_entry_tab


def _make_state(
    *, offset: int, page_size: int, total_count: int, entries_on_page: int
) -> TuiState:
    state = TuiState()
    state.page_size = page_size
    state.time_entry_tab.offset = offset
    state.time_entry_tab.total_count = total_count
    state.time_entry_tab.entries = cast(
        list[TimeEntry], [{"id": i} for i in range(entries_on_page)]
    )
    return state


class TestPageLabel:
    """_page_label() はステータスラインに出すページ表示文字列を返す"""

    def test_first_page_full(self):
        """page_size 25, total 87 で先頭ページなら 1/4 (1-25 / 87)"""
        state = _make_state(offset=0, page_size=25, total_count=87, entries_on_page=25)
        assert time_entry_tab._page_label(state) == "Page 1/4 (1-25 / 87)"

    def test_middle_page(self):
        """offset=25 (2ページ目) なら 2/4 (26-50 / 87)"""
        state = _make_state(offset=25, page_size=25, total_count=87, entries_on_page=25)
        assert time_entry_tab._page_label(state) == "Page 2/4 (26-50 / 87)"

    def test_last_partial_page(self):
        """最終ページが部分埋まり (12件) なら end は total に揃う"""
        state = _make_state(offset=75, page_size=25, total_count=87, entries_on_page=12)
        assert time_entry_tab._page_label(state) == "Page 4/4 (76-87 / 87)"

    def test_single_page_when_total_fits(self):
        """total <= page_size なら 1/1"""
        state = _make_state(offset=0, page_size=25, total_count=10, entries_on_page=10)
        assert time_entry_tab._page_label(state) == "Page 1/1 (1-10 / 10)"

    def test_empty_state_does_not_crash(self):
        """entries が空でも例外を投げない"""
        state = _make_state(offset=0, page_size=25, total_count=0, entries_on_page=0)
        assert time_entry_tab._page_label(state) == "Page 1/1 (0 / 0)"


class TestPageForward:
    """_on_page_forward() は次ページを取得して offset/cursor をリセットする"""

    def test_advances_offset_when_next_page_has_entries(self, monkeypatch):
        state = TuiState()
        state.page_size = 5
        state.time_entry_tab.offset = 0
        state.time_entry_tab.entries = cast(
            list[TimeEntry], [{"id": i} for i in range(1, 6)]
        )
        state.time_entry_tab.total_count = 12
        state.time_entry_tab.cursor = 3

        def fake_fetch(state, offset):
            assert offset == 5
            return {
                "time_entries": [{"id": i} for i in range(6, 11)],
                "total_count": 12,
                "issue_subjects": {},
            }

        monkeypatch.setattr(time_entry_tab, "_fetch_page_with_subjects", fake_fetch)

        time_entry_tab._on_page_forward(state)

        assert state.time_entry_tab.offset == 5
        assert state.time_entry_tab.cursor == 0
        assert len(state.time_entry_tab.entries) == 5

    def test_does_not_advance_when_next_page_is_empty(self, monkeypatch):
        """次ページが空ならカーソル/オフセットを動かさない (現ページ維持)"""
        state = TuiState()
        state.page_size = 5
        state.time_entry_tab.offset = 5
        state.time_entry_tab.entries = cast(
            list[TimeEntry], [{"id": i} for i in range(6, 11)]
        )
        state.time_entry_tab.total_count = 10
        state.time_entry_tab.cursor = 2

        monkeypatch.setattr(
            time_entry_tab,
            "_fetch_page_with_subjects",
            lambda state, offset: {
                "time_entries": [],
                "total_count": 10,
                "issue_subjects": {},
            },
        )

        time_entry_tab._on_page_forward(state)

        assert state.time_entry_tab.offset == 5
        assert state.time_entry_tab.cursor == 2
        assert len(state.time_entry_tab.entries) == 5


class TestPageBackward:
    """_on_page_backward() は前ページを取得する。先頭ページなら何もしない"""

    def test_moves_back_one_page(self, monkeypatch):
        state = TuiState()
        state.page_size = 5
        state.time_entry_tab.offset = 10
        state.time_entry_tab.entries = cast(
            list[TimeEntry], [{"id": i} for i in range(11, 16)]
        )
        state.time_entry_tab.total_count = 20
        state.time_entry_tab.cursor = 4

        def fake_fetch(state, offset):
            assert offset == 5
            return {
                "time_entries": [{"id": i} for i in range(6, 11)],
                "total_count": 20,
                "issue_subjects": {},
            }

        monkeypatch.setattr(time_entry_tab, "_fetch_page_with_subjects", fake_fetch)

        time_entry_tab._on_page_backward(state)

        assert state.time_entry_tab.offset == 5
        assert state.time_entry_tab.cursor == 0

    def test_does_nothing_on_first_page(self, monkeypatch):
        """offset=0 のときは fetch すら呼ばない"""
        state = TuiState()
        state.page_size = 5
        state.time_entry_tab.offset = 0
        state.time_entry_tab.entries = cast(list[TimeEntry], [{"id": 1}])
        state.time_entry_tab.cursor = 0

        called = False

        def fake_fetch(state, offset):
            nonlocal called
            called = True
            return {"time_entries": [], "total_count": 0, "issue_subjects": {}}

        monkeypatch.setattr(time_entry_tab, "_fetch_page_with_subjects", fake_fetch)

        time_entry_tab._on_page_backward(state)

        assert not called
        assert state.time_entry_tab.offset == 0


class TestFetchPageUsesFilter:
    """_fetch_page_with_subjects() は state.time_entry_tab.filter.user_id を API に渡す"""

    def test_default_filter_passes_me(self, monkeypatch):
        """デフォルトの filter (user_id='me') が API 呼び出しに伝わる"""
        state = TuiState()
        state.page_size = 5

        captured: dict = {}

        def fake_fetch(project_id, user_id, limit, offset):
            captured["user_id"] = user_id
            return {"time_entries": [], "total_count": 0}

        monkeypatch.setattr(time_entry_tab.time_entry_service, "fetch_page", fake_fetch)
        monkeypatch.setattr(
            time_entry_tab.time_entry_service,
            "fetch_issue_subjects",
            lambda entries: {},
        )

        time_entry_tab._fetch_page_with_subjects(state, 0)

        assert captured["user_id"] == "me"

    def test_no_filter_passes_none(self, monkeypatch):
        """user_id=None なら API には None が渡る (= フィルタしない)"""
        state = TuiState()
        state.page_size = 5
        state.time_entry_tab.filter.user_id = None
        state.time_entry_tab.filter.user_label = ""

        captured: dict = {}

        def fake_fetch(project_id, user_id, limit, offset):
            captured["user_id"] = user_id
            return {"time_entries": [], "total_count": 0}

        monkeypatch.setattr(time_entry_tab.time_entry_service, "fetch_page", fake_fetch)
        monkeypatch.setattr(
            time_entry_tab.time_entry_service,
            "fetch_issue_subjects",
            lambda entries: {},
        )

        time_entry_tab._fetch_page_with_subjects(state, 0)

        assert captured["user_id"] is None


class TestConfirmDelete:
    """confirm_delete() はカーソル行の削除を service に要求し、一覧を更新する"""

    def _state(self) -> TuiState:
        state = TuiState()
        state.time_entry_tab.entries = cast(list[TimeEntry], [{"id": 1}, {"id": 2}])
        state.time_entry_tab.total_count = 5
        state.time_entry_tab.cursor = 0
        return state

    def test_decrements_total_count(self, monkeypatch):
        """削除時は total_count を 1 減らしてページ表示の整合性を保つ"""
        state = self._state()
        deleted: list[str] = []
        monkeypatch.setattr(
            time_entry_tab.time_entry_service,
            "delete_time_entry",
            lambda time_entry_id: deleted.append(time_entry_id),
        )

        time_entry_tab.confirm_delete(state)

        assert deleted == [1]
        assert state.time_entry_tab.total_count == 4
        assert len(state.time_entry_tab.entries) == 1

    @pytest.mark.parametrize(
        ("error", "expected_in_flash"),
        [
            (TimeEntryNotFoundException(1), "1"),
            (requests.exceptions.ConnectionError("boom"), "boom"),
        ],
        ids=["time_entry_missing", "api_failure"],
    )
    def test_flashes_reason_on_failure(self, monkeypatch, error, expected_in_flash):
        """削除に失敗したら一覧を変えず、理由を flash_message に出す"""
        state = self._state()

        def fake_delete(time_entry_id: str) -> None:
            raise error

        monkeypatch.setattr(
            time_entry_tab.time_entry_service, "delete_time_entry", fake_delete
        )

        time_entry_tab.confirm_delete(state)

        assert state.time_entry_tab.total_count == 5
        assert len(state.time_entry_tab.entries) == 2
        assert state.flash_message is not None
        assert expected_in_flash in state.flash_message


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


def _summary_entries() -> list[TimeEntry]:
    return cast(
        list[TimeEntry],
        [
            {"id": 98, "spent_on": "2026-10-07", "hours": 0.5, "issue": {"id": 342}},
            {"id": 97, "spent_on": "2026-10-07", "hours": 3.0, "issue": {"id": 325}},
            {
                "id": 96,
                "spent_on": "2026-10-06",
                "hours": 4.0,
                "project": {"id": 1, "name": "redi"},
            },
        ],
    )


@pytest.fixture
def stub_summary_fetch(monkeypatch):
    """全件取得を固定の 3 件に差し替え、呼び出し条件を記録する。"""
    calls: list[dict] = []

    def fake_fetch_all(project_id, user_id):
        calls.append({"project_id": project_id, "user_id": user_id})
        return _summary_entries()

    monkeypatch.setattr(time_entry_tab.time_entry_service, "fetch_all", fake_fetch_all)
    monkeypatch.setattr(
        time_entry_tab.time_entry_service,
        "fetch_issue_subjects",
        lambda entries: {342: "config update", 325: "API 取得を非同期化"},
    )
    return calls


_TOTAL_LINE = messages.tui_time_entry_summary_total.format(hours="7.5", count=3)


def _list_text(state: TuiState) -> str:
    return "".join(text for _, text, *_ in time_entry_tab._render_list(state))


def _summary_rows(state: TuiState) -> list[str]:
    """集計ビューの行からカーソル印 (先頭 2 桁) を除いたもの。"""
    return [line[2:] for line in _list_text(state).splitlines()]


def _cursor_row(state: TuiState) -> str:
    return next(line[2:] for line in _list_text(state).splitlines() if line[:2] == "> ")


class TestToggleSummary:
    """toggle_summary() は一覧と、合計・日付ごとの集計ビューを切り替える"""

    def test_shows_total_and_tree_by_date(self, stub_summary_fetch):
        """合計と、日付ごとの合計の下にその日の作業時間を並べたツリーを表示する"""
        state = TuiState()

        time_entry_tab.toggle_summary(state)

        assert _summary_rows(state) == [
            _TOTAL_LINE,
            "2026-10-07  3.5h",
            "    #98  0.5h  #342 config update",
            "    #97  3.0h  #325 API 取得を非同期化",
            "2026-10-06  4.0h",
            "    #96  4.0h  redi",
        ]

    def test_uses_same_conditions_as_list(self, stub_summary_fetch):
        """集計は一覧と同じプロジェクト・ユーザーフィルタで全件を取る"""
        state = TuiState()
        state.project_id = "reditest"
        state.time_entry_tab.filter.user_id = "42"

        time_entry_tab.toggle_summary(state)

        assert stub_summary_fetch == [{"project_id": "reditest", "user_id": "42"}]

    def test_toggle_again_returns_to_list(self, stub_summary_fetch):
        """もう一度切り替えると一覧に戻る"""
        state = TuiState()
        state.time_entry_tab.loaded = True

        time_entry_tab.toggle_summary(state)
        time_entry_tab.toggle_summary(state)

        assert state.time_entry_tab.summary.show is False
        assert _list_text(state) == messages.tui_time_entry_no_entries

    def test_fetch_failure_shows_error(self, monkeypatch):
        """取得に失敗したら集計ビューに理由を出す"""

        def boom(project_id, user_id):
            raise requests.exceptions.ConnectionError("down")

        monkeypatch.setattr(time_entry_tab.time_entry_service, "fetch_all", boom)
        state = TuiState()

        time_entry_tab.toggle_summary(state)

        assert "down" in _list_text(state)


class TestSummaryView:
    """集計ビューを表示中の操作"""

    def test_jk_moves_cursor(self, stub_summary_fetch):
        """カーソルは先頭行から始まり、j / k で 1 行ずつ動く"""
        state = TuiState()
        time_entry_tab.toggle_summary(state)

        assert _cursor_row(state) == _TOTAL_LINE

        time_entry_tab._on_down(state)

        assert _cursor_row(state) == "2026-10-07  3.5h"

        time_entry_tab._on_up(state)

        assert _cursor_row(state) == _TOTAL_LINE

    def test_cursor_stays_within_lines(self, stub_summary_fetch):
        """先頭より上・末尾より下には動かない"""
        state = TuiState()
        time_entry_tab.toggle_summary(state)

        time_entry_tab._on_up(state)
        assert _cursor_row(state) == _TOTAL_LINE

        time_entry_tab._on_goto_bottom(state)
        time_entry_tab._on_down(state)
        assert _cursor_row(state) == "    #96  4.0h  redi"

    def test_list_window_follows_cursor(self, stub_summary_fetch):
        """一覧ペインがカーソル行を追って画面外に出さないよう、その行位置を返す"""
        state = TuiState()
        time_entry_tab.toggle_summary(state)

        time_entry_tab._on_goto_bottom(state)

        assert time_entry_tab.TIME_ENTRY_TAB.get_cursor_y(state) == 5

    def test_row_actions_are_disabled(self, stub_summary_fetch):
        """集計ビューのカーソルは見るためのもので、更新・作成・削除は効かない"""
        state = TuiState()
        state.time_entry_tab.entries = _summary_entries()
        time_entry_tab.toggle_summary(state)

        assert time_entry_tab._on_action_key(state, "u") is None
        assert time_entry_tab._on_action_key(state, "c") is None
        assert time_entry_tab.request_delete(state) is None

    def test_reload_fetches_summary_again(self, stub_summary_fetch):
        """R で集計を取り直す"""
        state = TuiState()
        time_entry_tab.toggle_summary(state)

        time_entry_tab._on_reload(state)

        assert len(stub_summary_fetch) == 2
