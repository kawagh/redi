from typing import cast

import pytest
import requests

from redi.api.time_entry import TimeEntry, TimeEntryNotFoundException
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

        monkeypatch.setattr(time_entry_tab, "fetch_time_entries_page", fake_fetch)
        monkeypatch.setattr(time_entry_tab, "fetch_issue_subjects", lambda ids: {})

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

        monkeypatch.setattr(time_entry_tab, "fetch_time_entries_page", fake_fetch)
        monkeypatch.setattr(time_entry_tab, "fetch_issue_subjects", lambda ids: {})

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

        assert deleted == ["1"]
        assert state.time_entry_tab.total_count == 4
        assert len(state.time_entry_tab.entries) == 1

    @pytest.mark.parametrize(
        ("error", "expected_in_flash"),
        [
            (TimeEntryNotFoundException("1"), "1"),
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
