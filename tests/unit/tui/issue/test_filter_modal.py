"""issues タブの f で開くフィルタ modal の単体テスト。"""

import asyncio
import inspect
from types import SimpleNamespace

import pytest
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from redi.tui.conditions import build_conditions
from redi.tui.issue import filter_modal
from redi.tui.issue.filter_modal import (
    open_filter_modal,
    section_cursor,
    shift_focus,
)
from redi.tui.keybindings import modal_keybindings
from redi.tui.state import IssueFilter, TuiState

STATUS_CHOICES = [(None, "open (default)"), ("closed", "closed only")]
ASSIGNEE_CHOICES = [(None, "(unspecified)"), ("me", "me")]
TRACKER_CHOICES = [(None, "(unspecified)"), ("1", "Bug"), ("2", "Feature")]
QUERY_CHOICES = [(None, "(unspecified)"), ("7", "My open issues")]


def _stub_choices(monkeypatch) -> None:
    monkeypatch.setattr(filter_modal, "build_status_choices", lambda: STATUS_CHOICES)
    monkeypatch.setattr(
        filter_modal,
        "build_assignee_choices",
        lambda _project_id, _me_id: ASSIGNEE_CHOICES,
    )
    monkeypatch.setattr(filter_modal, "build_tracker_choices", lambda: TRACKER_CHOICES)
    monkeypatch.setattr(
        filter_modal, "build_query_choices", lambda _project_id: QUERY_CHOICES
    )


class TestShiftFocus:
    """shift_focus() は 4 列を巡回して focus を動かす"""

    def test_moves_forward_through_all_sections(self):
        """右方向は status -> assignee -> tracker -> query -> status の順に巡回する"""
        assert shift_focus("status", 1) == "assignee"
        assert shift_focus("assignee", 1) == "tracker"
        assert shift_focus("tracker", 1) == "query"
        assert shift_focus("query", 1) == "status"

    def test_moves_backward_through_all_sections(self):
        """左方向は逆順に巡回する"""
        assert shift_focus("status", -1) == "query"
        assert shift_focus("query", -1) == "tracker"
        assert shift_focus("tracker", -1) == "assignee"
        assert shift_focus("assignee", -1) == "status"


class TestOpenFilterModal:
    """open_filter_modal() は選択肢を取り直して現在の絞り込みにカーソルを合わせる"""

    @pytest.mark.parametrize(
        ("issue_filter", "section", "expected_cursor"),
        [
            (IssueFilter(tracker_id="2", tracker_label="Feature"), "tracker", 2),
            (IssueFilter(query_id="7", query_label="My open issues"), "query", 1),
        ],
        ids=["tracker", "query"],
    )
    def test_puts_cursor_on_current_choice(
        self, monkeypatch, issue_filter, section, expected_cursor
    ):
        """適用中の絞り込みがある列は、その行にカーソルを合わせて開く"""
        _stub_choices(monkeypatch)
        state = TuiState()
        state.issue_tab.filter = issue_filter

        open_filter_modal(state)

        modal = state.issue_tab.filter_modal
        assert section_cursor(modal, section) == expected_cursor


def _handler(kb: KeyBindings, keys: tuple):
    """有効な filter を持つ最初のハンドラを返す。"""
    for binding in kb.get_bindings_for_keys(keys):
        if binding.filter():
            return binding.handler
    raise AssertionError(f"no active binding for {keys}")


def _press(kb: KeyBindings, keys: tuple) -> None:
    """キーを 1 つ処理する。再取得を伴うハンドラは coroutine なので走らせる。"""
    # 再取得のハンドラは event.app を再描画のために参照する。スピナー自体は
    # _kb() で素通しにしているので、参照できる形だけあればよい。
    event = SimpleNamespace(app=None)
    result = _handler(kb, keys)(event)
    if inspect.isawaitable(result):
        asyncio.run(result)


class TestFilterModalKeys:
    """フィルタ modal のキー操作で tracker を絞り込める"""

    def _kb(self, state: TuiState, monkeypatch) -> KeyBindings:
        monkeypatch.setattr(
            modal_keybindings, "reload_with_filter", lambda _state: None
        )

        # スピナーはスレッドと Application を要求するので、ここでは素通しにする。
        async def run_directly(_state, _app, _target, _label, fn):
            return fn()

        monkeypatch.setattr(modal_keybindings, "run_with_spinner", run_directly)
        kb = KeyBindings()
        modal_keybindings.register(kb, state, build_conditions(state))
        return kb

    def test_enter_applies_tracker(self, monkeypatch):
        """tracker 列で Enter を押すと tracker_id/tracker_label が反映される"""
        _stub_choices(monkeypatch)
        state = TuiState()
        open_filter_modal(state)
        kb = self._kb(state, monkeypatch)

        # tab を 2 回で status -> assignee -> tracker
        _press(kb, (Keys.ControlI,))
        _press(kb, (Keys.ControlI,))
        assert state.issue_tab.filter_modal.focus == "tracker"

        # j で「Bug」まで下げて Enter
        _press(kb, ("j",))
        _press(kb, (Keys.ControlM,))

        assert state.issue_tab.filter.tracker_id == "1"
        assert state.issue_tab.filter.tracker_label == "Bug"

    def test_clear_resets_all_columns(self, monkeypatch):
        """c を押すと全ての列の絞り込みもカーソルもクリアされる"""
        _stub_choices(monkeypatch)
        state = TuiState()
        state.issue_tab.filter = IssueFilter(tracker_id="1", tracker_label="Bug")
        open_filter_modal(state)
        modal = state.issue_tab.filter_modal
        modal.query_cursor = 1
        kb = self._kb(state, monkeypatch)

        _press(kb, ("c",))

        assert state.issue_tab.filter.is_active() is False
        assert modal.tracker_cursor == 0
        assert modal.query_cursor == 0

    def test_enter_applies_query_and_clears_other_conditions(self, monkeypatch):
        """クエリ列で Enter を押すと query_id が入り、他の絞り込みは外れる"""
        _stub_choices(monkeypatch)
        state = TuiState()
        state.issue_tab.filter = IssueFilter(tracker_id="1", tracker_label="Bug")
        open_filter_modal(state)
        kb = self._kb(state, monkeypatch)

        # tab を 3 回で status -> assignee -> tracker -> query
        for _ in range(3):
            _press(kb, (Keys.ControlI,))
        assert state.issue_tab.filter_modal.focus == "query"

        _press(kb, ("j",))
        _press(kb, (Keys.ControlM,))

        assert state.issue_tab.filter.query_id == "7"
        assert state.issue_tab.filter.query_label == "My open issues"
        assert state.issue_tab.filter.tracker_id is None
        # クリアされた列のカーソルも (unspecified) の行へ戻す
        assert state.issue_tab.filter_modal.tracker_cursor == 0
