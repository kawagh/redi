"""issues タブの f で開くフィルタ modal の単体テスト。"""

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from redi.tui.conditions import build_conditions
from redi.tui.issue import filter_modal
from redi.tui.issue.filter_modal import (
    open_filter_modal,
    render_filter_column,
    shift_focus,
)
from redi.tui.keybindings import modal_keybindings
from redi.tui.state import IssueFilter, TuiState

STATUS_CHOICES = [(None, "open (default)"), ("closed", "closed only")]
ASSIGNEE_CHOICES = [(None, "(unspecified)"), ("me", "me")]
TRACKER_CHOICES = [(None, "(unspecified)"), ("1", "Bug"), ("2", "Feature")]


def _stub_choices(monkeypatch) -> None:
    monkeypatch.setattr(filter_modal, "build_status_choices", lambda: STATUS_CHOICES)
    monkeypatch.setattr(
        filter_modal,
        "build_assignee_choices",
        lambda _project_id, _me_id: ASSIGNEE_CHOICES,
    )
    monkeypatch.setattr(filter_modal, "build_tracker_choices", lambda: TRACKER_CHOICES)


class TestShiftFocus:
    """shift_focus() は 3 列を巡回して focus を動かす"""

    def test_moves_forward_through_all_sections(self):
        """右方向は status -> assignee -> tracker -> status の順に巡回する"""
        assert shift_focus("status", 1) == "assignee"
        assert shift_focus("assignee", 1) == "tracker"
        assert shift_focus("tracker", 1) == "status"

    def test_moves_backward_through_all_sections(self):
        """左方向は逆順に巡回する"""
        assert shift_focus("status", -1) == "tracker"
        assert shift_focus("tracker", -1) == "assignee"
        assert shift_focus("assignee", -1) == "status"


class TestOpenFilterModal:
    """open_filter_modal() は選択肢を取り直して現在の絞り込みにカーソルを合わせる"""

    def test_puts_cursor_on_current_tracker(self, monkeypatch):
        """適用中の tracker があればその行にカーソルを合わせて開く"""
        _stub_choices(monkeypatch)
        state = TuiState()
        state.issue_tab.filter = IssueFilter(tracker_id="2", tracker_label="Feature")

        open_filter_modal(state)

        modal = state.issue_tab.filter_modal
        assert modal.tracker_choices == TRACKER_CHOICES
        assert modal.tracker_cursor == 2
        assert modal.focus == "status"
        assert modal.show is True

    def test_cursor_is_at_top_when_tracker_is_unset(self, monkeypatch):
        """tracker 未指定なら先頭 (指定なし) にカーソルを置く"""
        _stub_choices(monkeypatch)
        state = TuiState()

        open_filter_modal(state)

        assert state.issue_tab.filter_modal.tracker_cursor == 0


class TestRenderFilterColumn:
    """render_filter_column() は列ごとにヘッダと選択肢を描画する"""

    def test_marks_active_tracker(self, monkeypatch):
        """適用中の tracker の行に * を付ける"""
        _stub_choices(monkeypatch)
        state = TuiState()
        state.issue_tab.filter = IssueFilter(tracker_id="1", tracker_label="Bug")
        open_filter_modal(state)

        lines = "".join(
            text for _style, text in render_filter_column(state, "tracker")
        ).split("\n")

        assert lines[2] == "   * Bug"


def _handler(kb: KeyBindings, keys: tuple):
    """有効な filter を持つ最初のハンドラを返す。"""
    for binding in kb.get_bindings_for_keys(keys):
        if binding.filter():
            return binding.handler
    raise AssertionError(f"no active binding for {keys}")


class TestFilterModalKeys:
    """フィルタ modal のキー操作で tracker を絞り込める"""

    def _kb(self, state: TuiState, monkeypatch) -> KeyBindings:
        monkeypatch.setattr(
            modal_keybindings, "reload_with_filter", lambda _state: None
        )
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
        _handler(kb, (Keys.ControlI,))(None)
        _handler(kb, (Keys.ControlI,))(None)
        assert state.issue_tab.filter_modal.focus == "tracker"

        # j で「Bug」まで下げて Enter
        _handler(kb, ("j",))(None)
        _handler(kb, (Keys.ControlM,))(None)

        assert state.issue_tab.filter.tracker_id == "1"
        assert state.issue_tab.filter.tracker_label == "Bug"

    def test_clear_resets_tracker(self, monkeypatch):
        """c を押すと tracker の絞り込みもカーソルもクリアされる"""
        _stub_choices(monkeypatch)
        state = TuiState()
        state.issue_tab.filter = IssueFilter(tracker_id="1", tracker_label="Bug")
        open_filter_modal(state)
        kb = self._kb(state, monkeypatch)

        _handler(kb, ("c",))(None)

        assert state.issue_tab.filter.tracker_id is None
        assert state.issue_tab.filter_modal.tracker_cursor == 0
