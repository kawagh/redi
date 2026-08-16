from typing import cast

import requests

from redi.api.issue import Issue
from redi.tui.issue import delete_modal
from redi.tui.issue.delete_modal import confirm_delete, open_delete_modal
from redi.tui.state import TuiState


class _StubResponse:
    def __init__(self, status_code: int = 204):
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code}")


class TestOpenDeleteModal:
    """open_delete_modal() は対象 issue 情報をモーダル状態に書き込む"""

    def test_opens_with_target_id_and_subject(self):
        """カーソル位置の issue を target_id/target_subject に保持する"""
        state = TuiState()
        state.issue_tab.issues = cast(
            list[Issue],
            [
                {"id": 11, "subject": "first"},
                {"id": 22, "subject": "second"},
            ],
        )
        state.issue_tab.cursor = 1
        assert open_delete_modal(state) is True
        modal = state.issue_tab.delete_modal
        assert modal.show is True
        assert modal.target_id == 22
        assert modal.target_subject == "second"
        assert modal.input_text == ""
        assert modal.mismatch is False

    def test_returns_false_when_empty(self):
        """issues が空のときは modal を開かず False"""
        state = TuiState()
        assert open_delete_modal(state) is False
        assert state.issue_tab.delete_modal.show is False


class TestConfirmDelete:
    """confirm_delete() は modal の入力 id がカーソル行と一致したら削除する"""

    def _setup(self, state: TuiState, *, input_text: str) -> None:
        state.issue_tab.issues = cast(
            list[Issue],
            [
                {"id": 1, "subject": "a"},
                {"id": 2, "subject": "b"},
                {"id": 3, "subject": "c"},
            ],
        )
        state.issue_tab.cursor = 1
        state.issue_tab.total_count = 3
        open_delete_modal(state)
        state.issue_tab.delete_modal.input_text = input_text

    def test_removes_cursor_entry_when_id_matches(self, monkeypatch):
        """入力が target_id と一致すれば DELETE を発行し pop / total_count -1"""
        state = TuiState()
        self._setup(state, input_text="2")

        called: dict = {}

        def fake_delete(path: str):
            called["path"] = path
            return _StubResponse(204)

        monkeypatch.setattr(delete_modal.client, "delete", fake_delete)
        confirm_delete(state)

        assert called["path"] == "/issues/2.json"
        assert [i["id"] for i in state.issue_tab.issues] == [1, 3]
        assert state.issue_tab.total_count == 2
        assert state.issue_tab.cursor == 1
        assert state.issue_tab.delete_modal.show is False
        assert state.flash_message is None

    def test_mismatch_keeps_modal_open_and_clears_input(self, monkeypatch):
        """入力が一致しなければ削除せず mismatch=True で再入力を促す"""
        state = TuiState()
        self._setup(state, input_text="9")

        def fail(path: str):
            raise AssertionError("DELETE should not be called on mismatch")

        monkeypatch.setattr(delete_modal.client, "delete", fail)
        confirm_delete(state)

        assert [i["id"] for i in state.issue_tab.issues] == [1, 2, 3]
        assert state.issue_tab.delete_modal.show is True
        assert state.issue_tab.delete_modal.mismatch is True
        assert state.issue_tab.delete_modal.input_text == ""

    def test_clamps_cursor_when_deleting_last(self, monkeypatch):
        """末尾を削除した場合、cursor を新しい末尾にクランプする"""
        state = TuiState()
        state.issue_tab.issues = cast(list[Issue], [{"id": 1}, {"id": 2}])
        state.issue_tab.cursor = 1
        state.issue_tab.total_count = 2
        open_delete_modal(state)
        state.issue_tab.delete_modal.input_text = "2"

        monkeypatch.setattr(
            delete_modal.client, "delete", lambda path: _StubResponse(204)
        )
        confirm_delete(state)

        assert [i["id"] for i in state.issue_tab.issues] == [1]
        assert state.issue_tab.cursor == 0

    def test_sets_flash_message_on_api_failure(self, monkeypatch):
        """API エラー時は modal を閉じ、flash_message にメッセージを出す"""
        state = TuiState()
        state.issue_tab.issues = cast(list[Issue], [{"id": 1, "subject": "a"}])
        state.issue_tab.cursor = 0
        state.issue_tab.total_count = 1
        open_delete_modal(state)
        state.issue_tab.delete_modal.input_text = "1"

        def fake_delete(path: str):
            raise requests.exceptions.ConnectionError("boom")

        monkeypatch.setattr(delete_modal.client, "delete", fake_delete)
        confirm_delete(state)

        assert state.issue_tab.issues == [{"id": 1, "subject": "a"}]
        assert state.issue_tab.total_count == 1
        assert state.issue_tab.delete_modal.show is False
        assert state.flash_message is not None
        assert "boom" in state.flash_message


class TestInputDigit:
    """input_digit() は数字のみを入力欄に積み、mismatch 表示を消す"""

    def test_appends_digit_and_clears_mismatch(self):
        state = TuiState()
        state.issue_tab.delete_modal.mismatch = True
        delete_modal.input_digit(state, "1")
        delete_modal.input_digit(state, "2")
        assert state.issue_tab.delete_modal.input_text == "12"
        assert state.issue_tab.delete_modal.mismatch is False

    def test_ignores_non_digit(self):
        """数字以外 (英字や複数文字) は入力欄に入れない"""
        state = TuiState()
        delete_modal.input_digit(state, "a")
        delete_modal.input_digit(state, "12")
        assert state.issue_tab.delete_modal.input_text == ""
