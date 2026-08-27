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


class TestKeysWhileLoading:
    """API 取得中は一覧を動かすキーを受け付けない

    取得はワーカースレッドで走り、その間 issues / pages は書き換えられている。
    カーソルやページを動かすと壊れた組み合わせを描画しうるため一律で止める。
    """

    def _active(self, state: TuiState, keys: tuple) -> bool:
        return any(b.filter() for b in _kb(state).get_bindings_for_keys(keys))

    def test_movement_is_ignored(self):
        """取得中は j (カーソル移動) が効かない"""
        state = TuiState()
        state.loading.target = "list"

        assert self._active(state, ("j",)) is False

    def test_reload_is_ignored(self):
        """取得中は R が効かない (二重に取得を投げない)"""
        state = TuiState()
        state.loading.target = "list"

        assert self._active(state, ("R",)) is False

    def test_quit_still_works(self):
        """取得中でも q は効く

        サーバーが応答しないときに TUI から抜けられなくなるのを避ける。
        """
        state = TuiState()
        state.loading.target = "list"

        assert self._active(state, ("q",)) is True
