from typing import cast

import pytest
import requests

from redi.api.issue import Issue
from redi.i18n import messages
from redi.tui.issue import delete_modal
from redi.tui.issue.delete_modal import confirm_delete, open_delete_modal
from redi.tui.state import TuiState


@pytest.fixture
def deleted(monkeypatch) -> list[str]:
    """DELETE の呼び出し先を記録するスタブ。呼ばれなければ空のまま。"""
    paths: list[str] = []

    class _Response:
        def raise_for_status(self) -> None:
            pass

    def fake_delete(path: str) -> _Response:
        paths.append(path)
        return _Response()

    monkeypatch.setattr(delete_modal.client, "delete", fake_delete)
    return paths


def _open(state: TuiState, ids: list[int], *, cursor: int, input_text: str) -> None:
    """id が ids の issue 一覧を用意し、cursor 行を対象に modal を開いて入力する。"""
    state.issue_tab.issues = cast(
        list[Issue], [{"id": i, "subject": f"subject{i}"} for i in ids]
    )
    state.issue_tab.cursor = cursor
    state.issue_tab.total_count = len(ids)
    open_delete_modal(state)
    state.issue_tab.delete_modal.input_text = input_text


class TestOpenDeleteModal:
    """open_delete_modal() は対象 issue 情報をモーダル状態に書き込む"""

    def test_opens_with_target_id_and_subject(self):
        """カーソル位置の issue を target_id/target_subject に保持する"""
        state = TuiState()
        _open(state, [11, 22], cursor=1, input_text="")
        modal = state.issue_tab.delete_modal
        assert modal.show is True
        assert modal.target_id == 22
        assert modal.target_subject == "subject22"

    def test_clears_previous_input(self):
        """前回の入力や注意メッセージは持ち越さない"""
        state = TuiState()
        _open(state, [1, 2], cursor=0, input_text="99")
        state.issue_tab.delete_modal.notice = "dummy"

        assert open_delete_modal(state) is True

        assert state.issue_tab.delete_modal.input_text == ""
        assert state.issue_tab.delete_modal.notice is None

    def test_returns_false_when_empty(self):
        """issues が空のときは modal を開かず False"""
        state = TuiState()
        assert open_delete_modal(state) is False
        assert state.issue_tab.delete_modal.show is False


class TestConfirmDelete:
    """confirm_delete() は modal の入力 id が対象と一致したら削除する"""

    def test_removes_entry_when_id_matches(self, deleted):
        """入力が target_id と一致すれば DELETE を発行し pop / total_count -1"""
        state = TuiState()
        _open(state, [1, 2, 3], cursor=1, input_text="2")

        confirm_delete(state)

        assert deleted == ["/issues/2.json"]
        assert [i["id"] for i in state.issue_tab.issues] == [1, 3]
        assert state.issue_tab.total_count == 2
        assert state.issue_tab.delete_modal.show is False

    def test_mismatch_keeps_input(self, deleted):
        """入力が一致しなければ削除せず、入力はそのまま残して直させる"""
        state = TuiState()
        _open(state, [1, 2, 3], cursor=1, input_text="9")

        confirm_delete(state)

        assert deleted == []
        assert state.issue_tab.delete_modal.show is True
        assert (
            state.issue_tab.delete_modal.notice
            == messages.tui_issue_delete_modal_mismatch
        )
        assert state.issue_tab.delete_modal.input_text == "9"

    def test_empty_input_asks_for_issue_id(self, deleted):
        """入力が空のままなら削除せず issue_id の入力を促す"""
        state = TuiState()
        _open(state, [1, 2, 3], cursor=1, input_text="")

        confirm_delete(state)

        assert deleted == []
        assert state.issue_tab.delete_modal.show is True
        assert (
            state.issue_tab.delete_modal.notice == messages.tui_issue_delete_modal_empty
        )

    def test_clamps_cursor_when_deleting_last(self, deleted):
        """末尾を削除した場合、cursor を新しい末尾にクランプする"""
        state = TuiState()
        _open(state, [1, 2], cursor=1, input_text="2")

        confirm_delete(state)

        assert [i["id"] for i in state.issue_tab.issues] == [1]
        assert state.issue_tab.cursor == 0

    def test_sets_flash_message_on_api_failure(self, monkeypatch):
        """API エラー時は modal を閉じ、flash_message にメッセージを出す"""
        state = TuiState()
        _open(state, [1], cursor=0, input_text="1")

        def fake_delete(path: str):
            raise requests.exceptions.ConnectionError("boom")

        monkeypatch.setattr(delete_modal.client, "delete", fake_delete)
        confirm_delete(state)

        assert [i["id"] for i in state.issue_tab.issues] == [1]
        assert state.issue_tab.total_count == 1
        assert state.issue_tab.delete_modal.show is False
        assert state.flash_message is not None
        assert "boom" in state.flash_message


class TestInputDigit:
    """input_digit() は入力欄に数字を積み、notice を消す"""

    def test_appends_digit_and_clears_notice(self):
        """打ち始めた時点で直前の注意メッセージは消える"""
        state = TuiState()
        state.issue_tab.delete_modal.notice = "dummy"
        delete_modal.input_digit(state, "1")
        delete_modal.input_digit(state, "2")
        assert state.issue_tab.delete_modal.input_text == "12"
        assert state.issue_tab.delete_modal.notice is None
