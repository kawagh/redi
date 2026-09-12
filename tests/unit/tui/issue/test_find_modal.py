import pytest

from redi.tui.issue import find_modal, issue_tab
from redi.tui.state import IssueFind, TuiState


@pytest.fixture
def captured_offsets(monkeypatch) -> list[int]:
    """再取得が要求した offset を捕捉する (取得先の判定は issue_tab 側の責務)"""
    offsets: list[int] = []

    def fake_fetch(state: TuiState, offset: int) -> dict:
        offsets.append(offset)
        return {"issues": [{"id": 1, "subject": "hit"}], "total_count": 1}

    monkeypatch.setattr(issue_tab, "fetch_issues_with_filter", fake_fetch)
    return offsets


class TestOpenFindModal:
    """open_find_modal は打ち直しを省くために直前のクエリを引き継ぐ"""

    def test_initializes_input_with_current_query(self):
        """検索中に開くと入力欄が現在のクエリで埋まっている"""
        state = TuiState()
        state.issue_tab.find = IssueFind(query="hooks 調査")

        find_modal.open_find_modal(state)

        assert state.issue_tab.find_modal.show is True
        assert state.issue_tab.find_modal.input_text == "hooks 調査"

    def test_initializes_empty_when_not_searching(self):
        """検索していないときは空の入力欄で開く"""
        state = TuiState()

        find_modal.open_find_modal(state)

        assert state.issue_tab.find_modal.input_text == ""


class TestConfirmFind:
    """confirm_find は入力を検索条件に反映し、先頭ページから取り直す"""

    def test_applies_query_and_loads_first_page(self, captured_offsets):
        """クエリを確定すると検索条件になり、先頭ページを読み直す"""
        state = TuiState()
        state.issue_tab.offset = 50
        find_modal.open_find_modal(state)
        for char in "hooks":
            find_modal.input_char(state, char)

        find_modal.confirm_find(state)

        assert state.issue_tab.find.query == "hooks"
        assert captured_offsets == [0]
        assert state.issue_tab.offset == 0

    def test_empty_input_clears_search(self, captured_offsets):
        """空のまま確定すると検索が解除され、通常の一覧に戻る"""
        state = TuiState()
        state.issue_tab.find = IssueFind(query="hooks")
        find_modal.open_find_modal(state)
        for _ in range(len("hooks")):
            find_modal.backspace(state)

        find_modal.confirm_find(state)

        assert state.issue_tab.find.is_active() is False
        assert captured_offsets == [0]

    def test_whitespace_only_input_clears_search(self, captured_offsets):
        """空白だけの入力は検索と見なさず解除する"""
        state = TuiState()
        state.issue_tab.find = IssueFind(query="hooks")
        find_modal.open_find_modal(state)
        state.issue_tab.find_modal.input_text = "   "

        find_modal.confirm_find(state)

        assert state.issue_tab.find.is_active() is False

    def test_closes_modal_after_confirm(self, captured_offsets):
        """確定したら modal を閉じて入力をクリアする"""
        state = TuiState()
        find_modal.open_find_modal(state)
        find_modal.input_char(state, "x")

        find_modal.confirm_find(state)

        assert state.issue_tab.find_modal.show is False
        assert state.issue_tab.find_modal.input_text == ""


class TestCloseFindModal:
    """close_find_modal は検索条件を変えずに modal だけ閉じる"""

    def test_keeps_current_query(self):
        """Esc で閉じても実行中の検索は解除されない"""
        state = TuiState()
        state.issue_tab.find = IssueFind(query="hooks")
        find_modal.open_find_modal(state)
        find_modal.input_char(state, "z")

        find_modal.close_find_modal(state)

        assert state.issue_tab.find_modal.show is False
        assert state.issue_tab.find.query == "hooks"


class TestEditInput:
    """検索クエリは自由入力なので、末尾からまとめて消す手段を用意する"""

    def test_delete_word_removes_last_word(self):
        """C-w は末尾の1単語を消し、区切りの空白は残す"""
        state = TuiState()
        state.issue_tab.find_modal.input_text = "hooks 発火 調査"

        find_modal.delete_word(state)

        assert state.issue_tab.find_modal.input_text == "hooks 発火 "

    def test_delete_word_skips_trailing_spaces(self):
        """末尾が空白でも、その手前の単語まで遡って消す"""
        state = TuiState()
        state.issue_tab.find_modal.input_text = "hooks 発火   "

        find_modal.delete_word(state)

        assert state.issue_tab.find_modal.input_text == "hooks "

    def test_delete_word_handles_fullwidth_space(self):
        """全角スペースも単語の区切りとして扱う"""
        state = TuiState()
        state.issue_tab.find_modal.input_text = "hooks　発火"

        find_modal.delete_word(state)

        assert state.issue_tab.find_modal.input_text == "hooks　"

    def test_delete_word_on_empty_input(self):
        """空の入力欄で C-w を押しても例外にならない"""
        state = TuiState()

        find_modal.delete_word(state)

        assert state.issue_tab.find_modal.input_text == ""

    def test_clear_input_empties_the_field(self):
        """C-u は入力欄を空にする"""
        state = TuiState()
        state.issue_tab.find_modal.input_text = "hooks 発火 調査"

        find_modal.clear_input(state)

        assert state.issue_tab.find_modal.input_text == ""
