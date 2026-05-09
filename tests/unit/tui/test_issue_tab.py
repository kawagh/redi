from typing import cast

import requests

from redi.api.issue import Issue
from redi.tui import issue_tab
from redi.tui.issue_tab import (
    _page_label,
    close_delete_modal,
    confirm_delete,
    open_delete_modal,
)
from redi.tui.state import TuiState


def _make_state(
    *, offset: int, page_size: int, total_count: int, issues_on_page: int
) -> TuiState:
    state = TuiState()
    state.page_size = page_size
    state.issue_tab.offset = offset
    state.issue_tab.total_count = total_count
    state.issue_tab.issues = cast(
        list[Issue], [{"id": i, "subject": ""} for i in range(issues_on_page)]
    )
    return state


class TestPageLabel:
    """_page_label() はステータスラインに出すページ表示文字列を返す"""

    def test_first_page_full(self):
        """page_size 25, total 87 で先頭ページなら 1/4 (1-25 / 87)"""
        state = _make_state(offset=0, page_size=25, total_count=87, issues_on_page=25)
        assert _page_label(state) == "Page 1/4 (1-25 / 87)"

    def test_middle_page(self):
        """offset=25 (2ページ目) なら 2/4 (26-50 / 87)"""
        state = _make_state(offset=25, page_size=25, total_count=87, issues_on_page=25)
        assert _page_label(state) == "Page 2/4 (26-50 / 87)"

    def test_last_partial_page(self):
        """最終ページが部分埋まり (12件) なら end は total に揃う"""
        state = _make_state(offset=75, page_size=25, total_count=87, issues_on_page=12)
        assert _page_label(state) == "Page 4/4 (76-87 / 87)"

    def test_single_page_when_total_fits(self):
        """total <= page_size なら 1/1"""
        state = _make_state(offset=0, page_size=25, total_count=10, issues_on_page=10)
        assert _page_label(state) == "Page 1/1 (1-10 / 10)"

    def test_total_count_exact_multiple(self):
        """total が page_size の倍数のとき total_pages がずれない"""
        state = _make_state(offset=25, page_size=25, total_count=50, issues_on_page=25)
        assert _page_label(state) == "Page 2/2 (26-50 / 50)"

    def test_empty_state_does_not_crash(self):
        """issues が空でも例外を投げない (例: 0件のフィルタ結果)"""
        state = _make_state(offset=0, page_size=25, total_count=0, issues_on_page=0)
        assert _page_label(state) == "Page 1/1 (0 / 0)"


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

        monkeypatch.setattr(issue_tab.client, "delete", fake_delete)
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

        monkeypatch.setattr(issue_tab.client, "delete", fail)
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

        monkeypatch.setattr(issue_tab.client, "delete", lambda path: _StubResponse(204))
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

        monkeypatch.setattr(issue_tab.client, "delete", fake_delete)
        confirm_delete(state)

        assert state.issue_tab.issues == [{"id": 1, "subject": "a"}]
        assert state.issue_tab.total_count == 1
        assert state.issue_tab.delete_modal.show is False
        assert state.flash_message is not None
        assert "boom" in state.flash_message


class TestCloseDeleteModal:
    """close_delete_modal() は modal を閉じて入力をクリアする"""

    def test_clears_state(self):
        state = TuiState()
        state.issue_tab.issues = cast(list[Issue], [{"id": 1, "subject": "a"}])
        open_delete_modal(state)
        state.issue_tab.delete_modal.input_text = "12"
        state.issue_tab.delete_modal.mismatch = True

        close_delete_modal(state)

        assert state.issue_tab.delete_modal.show is False
        assert state.issue_tab.delete_modal.input_text == ""
        assert state.issue_tab.delete_modal.mismatch is False
