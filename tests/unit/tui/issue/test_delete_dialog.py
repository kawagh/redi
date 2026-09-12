from typing import cast

import pytest
import requests

from redi.api.issue import Issue, IssueNotFoundException
from redi.i18n import messages
from redi.tui.issue import delete_dialog
from redi.tui.issue.delete_dialog import (
    confirm_delete,
    open_delete_dialog,
    validate_input,
)
from redi.tui.state import TuiState


@pytest.fixture
def deleted(monkeypatch) -> list[str]:
    """service への削除要求を記録するスタブ。呼ばれなければ空のまま。"""
    ids: list[str] = []

    def fake_delete_issue(issue_id: str) -> None:
        ids.append(issue_id)

    monkeypatch.setattr(delete_dialog.issue_service, "delete_issue", fake_delete_issue)
    return ids


def _open(state: TuiState, ids: list[int], *, cursor: int, input_text: str) -> None:
    """id が ids の issue 一覧を用意し、cursor 行を対象にダイアログを開いて入力する。"""
    state.issue_tab.issues = cast(
        list[Issue], [{"id": i, "subject": f"subject{i}"} for i in ids]
    )
    state.issue_tab.cursor = cursor
    state.issue_tab.total_count = len(ids)
    open_delete_dialog(state)
    state.issue_tab.delete_dialog.input_text = input_text


class TestOpenDeleteDialog:
    """open_delete_dialog() は対象 issue 情報をダイアログ状態に書き込む"""

    def test_opens_with_target_id_and_subject(self):
        """カーソル位置の issue を target_id/target_subject に保持する"""
        state = TuiState()
        _open(state, [11, 22], cursor=1, input_text="")
        dialog = state.issue_tab.delete_dialog
        assert dialog.show is True
        assert dialog.target_id == 22
        assert dialog.target_subject == "subject22"

    def test_clears_previous_input(self):
        """前回の入力や注意メッセージは持ち越さない"""
        state = TuiState()
        _open(state, [1, 2], cursor=0, input_text="99")
        state.issue_tab.delete_dialog.notice = "dummy"

        assert open_delete_dialog(state) is True

        assert state.issue_tab.delete_dialog.input_text == ""
        assert state.issue_tab.delete_dialog.notice is None

    def test_returns_false_when_empty(self):
        """issues が空のときはダイアログを開かず False"""
        state = TuiState()
        assert open_delete_dialog(state) is False
        assert state.issue_tab.delete_dialog.show is False


class TestValidateInput:
    """validate_input() は入力が対象 id と一致しない理由を返す"""

    def test_returns_none_when_matches(self):
        """target_id と一致すれば理由なし (None)"""
        state = TuiState()
        _open(state, [1, 2], cursor=1, input_text="2")

        assert validate_input(state.issue_tab.delete_dialog) is None

    def test_asks_input_when_empty(self):
        """未入力なら issue_id の入力を促す"""
        state = TuiState()
        _open(state, [1, 2], cursor=1, input_text="")

        assert (
            validate_input(state.issue_tab.delete_dialog)
            == messages.tui_issue_delete_dialog_empty
        )

    def test_reports_mismatch(self):
        """target_id と違う入力は不一致として返す"""
        state = TuiState()
        _open(state, [1, 2], cursor=1, input_text="9")

        assert (
            validate_input(state.issue_tab.delete_dialog)
            == messages.tui_issue_delete_dialog_mismatch
        )


class TestConfirmDelete:
    """confirm_delete() はダイアログの入力 id が対象と一致したら削除する"""

    def test_removes_entry_when_id_matches(self, deleted):
        """入力が target_id と一致すれば削除を要求し pop / total_count -1"""
        state = TuiState()
        _open(state, [1, 2, 3], cursor=1, input_text="2")

        confirm_delete(state)

        assert deleted == ["2"]
        assert [i["id"] for i in state.issue_tab.issues] == [1, 3]
        assert state.issue_tab.total_count == 2
        assert state.issue_tab.delete_dialog.show is False

    def test_mismatch_keeps_input(self, deleted):
        """入力が一致しなければ削除せず、入力はそのまま残して直させる"""
        state = TuiState()
        _open(state, [1, 2, 3], cursor=1, input_text="9")

        confirm_delete(state)

        assert deleted == []
        assert state.issue_tab.delete_dialog.show is True
        assert (
            state.issue_tab.delete_dialog.notice
            == messages.tui_issue_delete_dialog_mismatch
        )
        assert state.issue_tab.delete_dialog.input_text == "9"

    def test_empty_input_asks_for_issue_id(self, deleted):
        """入力が空のままなら削除せず issue_id の入力を促す"""
        state = TuiState()
        _open(state, [1, 2, 3], cursor=1, input_text="")

        confirm_delete(state)

        assert deleted == []
        assert state.issue_tab.delete_dialog.show is True
        assert (
            state.issue_tab.delete_dialog.notice
            == messages.tui_issue_delete_dialog_empty
        )

    def test_clamps_cursor_when_deleting_last(self, deleted):
        """末尾を削除した場合、cursor を新しい末尾にクランプする"""
        state = TuiState()
        _open(state, [1, 2], cursor=1, input_text="2")

        confirm_delete(state)

        assert [i["id"] for i in state.issue_tab.issues] == [1]
        assert state.issue_tab.cursor == 0

    @pytest.mark.parametrize(
        ("error", "expected_in_flash"),
        [
            (IssueNotFoundException("1"), "1"),
            (requests.exceptions.ConnectionError("boom"), "boom"),
        ],
        ids=["issue_missing", "api_failure"],
    )
    def test_flashes_reason_on_failure(self, monkeypatch, error, expected_in_flash):
        """削除に失敗したら一覧を変えず、ダイアログを閉じて理由を flash_message に出す"""
        state = TuiState()
        _open(state, [1], cursor=0, input_text="1")

        def fake_delete_issue(issue_id: str) -> None:
            raise error

        monkeypatch.setattr(
            delete_dialog.issue_service, "delete_issue", fake_delete_issue
        )
        confirm_delete(state)

        assert [i["id"] for i in state.issue_tab.issues] == [1]
        assert state.issue_tab.total_count == 1
        assert state.issue_tab.delete_dialog.show is False
        assert state.flash_message is not None
        assert expected_in_flash in state.flash_message


class TestInputDigit:
    """input_digit() は入力欄に数字を積み、notice を消す"""

    def test_appends_digit_and_clears_notice(self):
        """打ち始めた時点で直前の注意メッセージは消える"""
        state = TuiState()
        state.issue_tab.delete_dialog.notice = "dummy"
        delete_dialog.input_digit(state, "1")
        delete_dialog.input_digit(state, "2")
        assert state.issue_tab.delete_dialog.input_text == "12"
        assert state.issue_tab.delete_dialog.notice is None
