"""検索 (F) とフィルタ (f) の切り替え挙動の単体テスト。

検索中は検索結果がフィルタを置き換えるので、フィルタを触っても一覧が変わらない。
黙って空振りさせず「最後に触った方が勝つ」ようにしていることを固定する。
"""

import pytest
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from redi.i18n import messages
from redi.tui.conditions import build_conditions
from redi.tui.issue import issue_tab
from redi.tui.keybindings import modal_keybindings
from redi.tui.state import IssueFilter, IssueFind, TuiState


def _handler(kb: KeyBindings, keys: tuple):
    """有効な filter を持つハンドラを返す。<any> より具体的なものを優先する。"""
    for binding in reversed(kb.get_bindings_for_keys(keys)):
        if binding.filter():
            return binding.handler
    raise AssertionError(f"no active binding for {keys}")


def _kb(state: TuiState) -> KeyBindings:
    kb = KeyBindings()
    modal_keybindings.register(kb, state, build_conditions(state))
    return kb


@pytest.fixture
def searching_state(monkeypatch) -> TuiState:
    """検索中で、かつ検索前のフィルタを保持している状態を作る"""
    monkeypatch.setattr(
        issue_tab,
        "fetch_issues_with_filter",
        lambda state, offset: {"issues": [], "total_count": 0},
    )
    state = TuiState()
    state.page_size = 5
    state.tab = "issues"
    state.issue_tab.filter = IssueFilter(status_id="closed", status_label="終了")
    state.issue_tab.find = IssueFind(query="hooks")
    state.issue_tab.filter_modal.show = True
    state.issue_tab.filter_modal.status_choices = [("open", "未完了")]
    return state


class TestFilterWinsOverFind:
    """検索中にフィルタを適用すると、検索を解除してフィルタに切り替える"""

    def test_apply_clears_find(self, searching_state):
        """フィルタの適用は検索を解除する (適用が空振りしないように)"""
        _handler(_kb(searching_state), (Keys.ControlM,))(None)

        assert searching_state.issue_tab.find.is_active() is False

    def test_apply_notifies_the_switch(self, searching_state):
        """切り替わったことを flash で伝える"""
        _handler(_kb(searching_state), (Keys.ControlM,))(None)

        assert (
            searching_state.flash_message == messages.tui_flash_find_cleared_by_filter
        )

    def test_clear_all_clears_find(self, searching_state):
        """フィルタの全クリア (c) も同じく検索を解除する"""
        _handler(_kb(searching_state), ("c",))(None)

        assert searching_state.issue_tab.find.is_active() is False
        assert (
            searching_state.flash_message == messages.tui_flash_find_cleared_by_filter
        )

    def test_no_flash_when_not_searching(self, monkeypatch):
        """検索していないときのフィルタ適用は今までどおり何も通知しない"""
        monkeypatch.setattr(
            issue_tab,
            "fetch_issues_with_filter",
            lambda state, offset: {"issues": [], "total_count": 0},
        )
        state = TuiState()
        state.page_size = 5
        state.issue_tab.filter_modal.show = True
        state.issue_tab.filter_modal.status_choices = [("open", "未完了")]

        _handler(_kb(state), (Keys.ControlM,))(None)

        assert state.flash_message is None
