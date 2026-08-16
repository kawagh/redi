from typing import cast

import pytest
import requests

from redi.api.wiki import WikiPage
from redi.i18n import messages
from redi.service.wiki_service import WikiPageNotFoundError
from redi.tui.state import TuiState
from redi.tui.wiki import delete_modal
from redi.tui.wiki.delete_modal import (
    CONFIRM_WORD,
    apply_deleted,
    confirm_delete,
    open_delete_modal,
    validate_input,
)
from redi.tui.wiki.wiki_tab import set_pages


def _page(title: str, parent: str | None = None) -> WikiPage:
    page: dict = {"title": title, "version": 1}
    if parent is not None:
        page["parent"] = {"title": parent}
    return cast(WikiPage, page)


def _state(pages: list[WikiPage], *, cursor: int = 0) -> TuiState:
    """pages を持つ wiki タブの state を作る。labels は表示と同じツリー順で作る。"""
    state = TuiState()
    state.tab = "wiki"
    set_pages(state, pages)
    state.wiki_tab.cursor = cursor
    return state


def _titles(state: TuiState) -> list[str]:
    return [page["title"] for page in state.wiki_tab.pages]


class TestOpenDeleteModal:
    """open_delete_modal() は対象ページを modal 状態に書き込む"""

    def test_opens_with_target_title(self):
        """カーソル位置のページタイトルを target_title に保持する"""
        state = _state([_page("Guide"), _page("Home")], cursor=1)

        assert open_delete_modal(state) is True

        assert state.wiki_tab.delete_modal.show is True
        assert state.wiki_tab.delete_modal.target_title == "Home"

    def test_clears_previous_input(self):
        """前回の入力や注意メッセージは持ち越さない"""
        state = _state([_page("Home")])
        state.wiki_tab.delete_modal.input_text = "DEL"
        state.wiki_tab.delete_modal.notice = "dummy"

        open_delete_modal(state)

        assert state.wiki_tab.delete_modal.input_text == ""
        assert state.wiki_tab.delete_modal.notice is None

    def test_returns_false_when_empty(self):
        """ページが無いときは modal を開かず False"""
        state = _state([])

        assert open_delete_modal(state) is False
        assert state.wiki_tab.delete_modal.show is False


class TestValidateInput:
    """validate_input() は確認語と一致しない理由を返す"""

    def test_returns_none_when_matches(self):
        """確認語と一致すれば理由なし (None)"""
        state = _state([_page("Home")])
        state.wiki_tab.delete_modal.input_text = CONFIRM_WORD

        assert validate_input(state.wiki_tab.delete_modal) is None

    def test_asks_input_when_empty(self):
        """未入力なら確認語の入力を促す"""
        state = _state([_page("Home")])

        assert validate_input(
            state.wiki_tab.delete_modal
        ) == messages.tui_wiki_delete_modal_empty.format(expected=CONFIRM_WORD)

    def test_reports_mismatch(self):
        """確認語と違う入力は不一致として返す"""
        state = _state([_page("Home")])
        state.wiki_tab.delete_modal.input_text = "DELET"

        assert validate_input(
            state.wiki_tab.delete_modal
        ) == messages.tui_wiki_delete_modal_mismatch.format(expected=CONFIRM_WORD)


class TestApplyDeleted:
    """apply_deleted() は削除済みページを一覧から取り除く"""

    def test_removes_page(self):
        """対象ページを一覧から取り除く"""
        state = _state([_page("Guide"), _page("Home")])

        apply_deleted(state, "Guide")

        assert _titles(state) == ["Home"]

    def test_promotes_children_to_top_level(self):
        """親を削除しても子ページは残り、Redmine と同じく最上位に繰り上がる"""
        state = _state(
            [
                _page("Guide"),
                _page("Home"),
                _page("Setup", parent="Guide"),
                _page("Detail", parent="Setup"),
            ]
        )

        apply_deleted(state, "Guide")

        assert _titles(state) == ["Home", "Setup", "Detail"]
        assert state.wiki_tab.labels == [
            "├── Home",
            "└── Setup",
            "    └── Detail",
        ]

    def test_drops_loaded_text(self):
        """読み込み済みの本文も削除したページのぶんだけ捨てる"""
        state = _state([_page("Guide"), _page("Home")])
        state.wiki_tab.texts = {"Home": "home body", "Guide": "guide body"}

        apply_deleted(state, "Guide")

        assert state.wiki_tab.texts == {"Home": "home body"}

    def test_clamps_cursor_when_deleting_last(self):
        """末尾を削除した場合、cursor を新しい末尾にクランプする"""
        state = _state([_page("Guide"), _page("Home")], cursor=1)

        apply_deleted(state, "Home")

        assert state.wiki_tab.cursor == 0


class TestConfirmDelete:
    """confirm_delete() は入力が確認語と一致したときだけ削除を要求する"""

    @pytest.fixture
    def deleted(self, monkeypatch) -> list[tuple[str, str]]:
        """service への削除要求を記録するスタブ。呼ばれなければ空のまま。"""
        calls: list[tuple[str, str]] = []

        def fake_delete_page(project_id: str, page_title: str) -> None:
            calls.append((project_id, page_title))

        monkeypatch.setattr(delete_modal.wiki_service, "delete_page", fake_delete_page)
        return calls

    def _opened(self, input_text: str) -> TuiState:
        state = _state([_page("Guide"), _page("Home")], cursor=1)
        state.project_id = "myproject"
        open_delete_modal(state)
        state.wiki_tab.delete_modal.input_text = input_text
        return state

    def test_deletes_when_input_matches(self, deleted):
        """確認語と一致すれば削除を要求し、一覧から取り除いて modal を閉じる"""
        state = self._opened(CONFIRM_WORD)

        confirm_delete(state)

        assert deleted == [("myproject", "Home")]
        assert _titles(state) == ["Guide"]
        assert state.wiki_tab.delete_modal.show is False

    def test_mismatch_keeps_input(self, deleted):
        """一致しなければ削除せず、入力はそのまま残して直させる"""
        state = self._opened("DELET")

        confirm_delete(state)

        assert deleted == []
        assert state.wiki_tab.delete_modal.show is True
        assert state.wiki_tab.delete_modal.input_text == "DELET"
        assert state.wiki_tab.delete_modal.notice is not None

    @pytest.mark.parametrize(
        ("error", "expected_in_flash"),
        [
            (WikiPageNotFoundError("Home"), "Home"),
            (requests.exceptions.ConnectionError("boom"), "boom"),
        ],
        ids=["page_missing", "api_failure"],
    )
    def test_flashes_reason_on_failure(self, monkeypatch, error, expected_in_flash):
        """削除に失敗したら一覧を変えず、modal を閉じて理由を flash_message に出す"""
        state = self._opened(CONFIRM_WORD)

        def fake_delete_page(project_id: str, page_title: str) -> None:
            raise error

        monkeypatch.setattr(delete_modal.wiki_service, "delete_page", fake_delete_page)
        confirm_delete(state)

        assert _titles(state) == ["Guide", "Home"]
        assert state.wiki_tab.delete_modal.show is False
        assert state.flash_message is not None
        assert expected_in_flash in state.flash_message
