from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from redi.tui.conditions import build_conditions
from redi.tui.keybindings import normal_keybindings
from redi.tui.state import IssueFilter, TuiState


def _handler(kb: KeyBindings, keys: tuple):
    """有効な filter を持つ最初のハンドラを返す。"""
    for binding in kb.get_bindings_for_keys(keys):
        if binding.filter():
            return binding.handler
    raise AssertionError(f"no active binding for {keys}")


def _kb(state: TuiState) -> KeyBindings:
    kb = KeyBindings()
    normal_keybindings.register(kb, state, build_conditions(state))
    return kb


class TestEscapeClearsSearch:
    """通常モードの Esc は残っている検索クエリを解除する"""

    def test_clears_search_query(self):
        """検索確定後に Esc を押すとクエリが消える (n がコメント追加に戻る)"""
        state = TuiState()
        state.search_query = "foo"

        _handler(_kb(state), (Keys.Escape,))(None)

        assert state.search_query == ""

    def test_keeps_filter(self):
        """Esc が解除するのは検索だけで、適用中のフィルタは残す"""
        state = TuiState()
        state.search_query = "foo"
        state.issue_tab.filter = IssueFilter(tracker_id="2", tracker_label="Feature")

        _handler(_kb(state), (Keys.Escape,))(None)

        assert state.issue_tab.filter.tracker_id == "2"
