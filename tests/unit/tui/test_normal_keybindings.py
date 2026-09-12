import pytest
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from redi.tui.conditions import build_conditions
from redi.tui.keybindings import normal_keybindings
from redi.tui.state import TuiState
from redi.tui.state.issue_tab import IssueFilter


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


class TestFindKey:
    """F は issue タブでだけ検索ダイアログを開く"""

    def test_opens_find_dialog_on_issue_tab(self):
        """issues タブで F を押すと検索ダイアログが開く"""
        state = TuiState()
        state.tab = "issues"

        _handler(_kb(state), ("F",))(None)

        assert state.issue_tab.find_dialog.show is True

    def test_does_nothing_on_other_tabs(self):
        """wiki タブには検索がないので F を押してもダイアログは開かない"""
        state = TuiState()
        state.tab = "wiki"

        _handler(_kb(state), ("F",))(None)

        assert state.issue_tab.find_dialog.show is False

    def test_find_dialog_disables_normal_keys(self):
        """検索ダイアログ表示中は通常モードのキーが効かない"""
        state = TuiState()
        state.tab = "issues"
        state.issue_tab.find_dialog.show = True

        with pytest.raises(AssertionError):
            _handler(_kb(state), ("F",))


class TestWikiVersionKey:
    """H は wiki タブでだけ版の表示に使う"""

    def _wiki_state(self) -> TuiState:
        from typing import cast

        from redi.api.wiki import WikiPage
        from redi.tui.wiki.wiki_tab import set_pages

        state = TuiState()
        state.tab = "wiki"
        set_pages(state, [cast(WikiPage, {"title": "Home", "version": 3})])
        return state

    def test_opens_version_dialog(self):
        """wiki タブで h を押すと版選択ダイアログが開く"""
        state = self._wiki_state()

        _handler(_kb(state), ("h",))(None)

        assert state.wiki_tab.version_dialog.show is True

    def test_d_opens_diff_dialog(self):
        """wiki タブで d を押すと比較する版を選ぶダイアログが開く"""
        state = self._wiki_state()

        _handler(_kb(state), ("d",))(None)

        assert state.wiki_tab.diff_dialog.show is True

    def test_does_nothing_on_other_tabs(self):
        """issues タブで h を押しても版選択ダイアログは開かない (ページ送りのまま)"""
        state = TuiState()
        state.tab = "issues"

        _handler(_kb(state), ("h",))(None)

        assert state.wiki_tab.version_dialog.show is False

    def test_version_dialog_disables_normal_keys(self):
        """版選択ダイアログ表示中は通常モードのキーが効かない"""
        state = self._wiki_state()
        state.wiki_tab.version_dialog.show = True

        with pytest.raises(AssertionError):
            _handler(_kb(state), ("h",))
