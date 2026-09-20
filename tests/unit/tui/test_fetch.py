"""TUI を止めずに API を取得する仕組み (run_fetch) の単体テスト。"""

import asyncio
import threading
from typing import cast

import requests

from redi.api.issue import Issue
from redi.i18n import messages
from redi.tui.issue import issue_tab
from redi.tui.state import TuiState

FETCH_WAIT_SECONDS = 5


def _issues(*ids: int) -> list[Issue]:
    return cast(list[Issue], [{"id": i, "subject": f"issue-{i}"} for i in ids])


class _Hold:
    """応答を止めているリクエスト。`release()` で応答を返す。"""

    def __init__(self):
        self.started = threading.Event()
        self.released = threading.Event()

    async def wait_started(self) -> None:
        assert await asyncio.to_thread(self.started.wait, FETCH_WAIT_SECONDS)

    def release(self) -> None:
        self.released.set()


class _FakeRedmine:
    """issue 一覧 API の代わり。id が 1 から `total` までの issue を持つ。

    `hold(offset)` すると、そのページへの次のリクエストは `release()` まで応答しない。
    遅い Redmine の代わり。
    """

    def __init__(self, monkeypatch, total: int):
        self.total = total
        self.fail = False
        self.requested: list[int] = []
        self._holds: dict[int, _Hold] = {}
        monkeypatch.setattr(issue_tab, "fetch_issues_page", self._fetch_issues_page)

    def hold(self, offset: int) -> _Hold:
        self._holds[offset] = _Hold()
        return self._holds[offset]

    def _fetch_issues_page(self, *, offset: int, limit: int, **_):
        self.requested.append(offset)
        last_id = min(offset + limit, self.total)
        page = {
            "issues": _issues(*range(offset + 1, last_id + 1)),
            "total_count": self.total,
        }
        hold = self._holds.pop(offset, None)
        if hold is not None:
            hold.started.set()
            assert hold.released.wait(FETCH_WAIT_SECONDS)
        if self.fail:
            raise requests.exceptions.ConnectionError("boom")
        return page


def _state_showing(redmine: _FakeRedmine, *, offset: int, page_size: int) -> TuiState:
    """`offset` のページを表示している state。"""
    state = TuiState()
    state.page_size = page_size
    issue_tab._show(
        state, issue_tab.fetch_issues_with_filter(state, offset), offset, cursor=0
    )
    redmine.requested.clear()
    return state


class TestIssueReloadDoesNotBlock:
    """issue タブの再読込は、応答を待つ間も TUI の操作を止めない"""

    def test_cursor_moves_while_fetching(self, monkeypatch):
        """取得中もカーソルを動かせて、結果が届いた後もその位置が保たれる"""
        redmine = _FakeRedmine(monkeypatch, total=5)
        state = _state_showing(redmine, offset=0, page_size=5)
        hold = redmine.hold(0)

        async def scenario():
            reloading = asyncio.create_task(issue_tab._on_reload(state))
            await hold.wait_started()
            assert state.fetching == 1
            assert state.flash_message == messages.tui_flash_fetching
            issue_tab.ISSUE_TAB.on_down(state)
            issue_tab.ISSUE_TAB.on_down(state)
            assert state.issue_tab.cursor == 2
            hold.release()
            await reloading

        asyncio.run(scenario())

        assert state.issue_tab.cursor == 2
        assert state.fetching == 0
        assert state.flash_message == messages.tui_flash_reloaded

    def test_discards_result_when_conditions_changed_while_fetching(self, monkeypatch):
        """取得中に絞り込みを変えて一覧を取り直したら、後から届いた前の条件の結果で上書きしない"""
        redmine = _FakeRedmine(monkeypatch, total=3)
        state = _state_showing(redmine, offset=0, page_size=3)
        hold = redmine.hold(0)

        async def scenario():
            reloading = asyncio.create_task(issue_tab._on_reload(state))
            await hold.wait_started()
            state.issue_tab.filter.apply("status", "closed", "closed")
            redmine.total = 2
            issue_tab.reload_with_filter(state)
            hold.release()
            await reloading

        asyncio.run(scenario())

        assert state.issue_tab.issues == _issues(1, 2)

    def test_keeps_the_list_while_selecting_a_comment(self, monkeypatch):
        """取得中にコメント選択へ入ったら、届いた結果で一覧を差し替えない

        コメント選択は表示中の一覧の journals を指しているため。
        """
        redmine = _FakeRedmine(monkeypatch, total=3)
        state = _state_showing(redmine, offset=0, page_size=3)
        shown = state.issue_tab.issues
        hold = redmine.hold(0)

        async def scenario():
            reloading = asyncio.create_task(issue_tab._on_reload(state))
            await hold.wait_started()
            state.issue_tab.comment_select.active = True
            hold.release()
            await reloading

        asyncio.run(scenario())

        assert state.issue_tab.issues is shown

    def test_fetch_failure_is_shown_and_keeps_the_list(self, monkeypatch):
        """取得に失敗したら通知を出し、例外は漏らさず一覧も保つ"""
        redmine = _FakeRedmine(monkeypatch, total=3)
        state = _state_showing(redmine, offset=0, page_size=3)
        redmine.fail = True

        asyncio.run(issue_tab._on_reload(state))

        assert state.issue_tab.issues == _issues(1, 2, 3)
        assert state.flash_message == messages.tui_flash_fetch_failed.format(
            error="boom"
        )
        assert state.fetching == 0


class TestIssuePagingDoesNotBlock:
    """issue タブのページ送りは、応答を待つ間も次の操作を受け付ける"""

    def test_paging_again_while_fetching_advances_from_the_requested_page(
        self, monkeypatch
    ):
        """取得中にもう一度ページを送ると、届く前のページの次へ進み、遅れて届いた手前のページは捨てる"""
        redmine = _FakeRedmine(monkeypatch, total=9)
        state = _state_showing(redmine, offset=0, page_size=3)
        hold = redmine.hold(3)

        async def scenario():
            first = asyncio.create_task(issue_tab._on_page_forward(state))
            await hold.wait_started()
            await issue_tab._on_page_forward(state)
            hold.release()
            await first

        asyncio.run(scenario())

        assert redmine.requested == [3, 6]
        assert state.issue_tab.offset == 6
        assert state.issue_tab.issues == _issues(7, 8, 9)

    def test_does_not_page_beyond_the_last_page(self, monkeypatch):
        """最終ページ (取得中の行き先を含む) より先へは送らない"""
        redmine = _FakeRedmine(monkeypatch, total=9)
        state = _state_showing(redmine, offset=3, page_size=3)
        hold = redmine.hold(6)

        async def scenario():
            last = asyncio.create_task(issue_tab._on_page_forward(state))
            await hold.wait_started()
            await issue_tab._on_page_forward(state)
            hold.release()
            await last

        asyncio.run(scenario())

        assert redmine.requested == [6]
        assert state.issue_tab.offset == 6

    def test_failure_keeps_the_page_and_the_next_paging_starts_from_it(
        self, monkeypatch
    ):
        """取得に失敗したら今のページに留まり、次のページ送りは今のページから数える"""
        redmine = _FakeRedmine(monkeypatch, total=9)
        state = _state_showing(redmine, offset=0, page_size=3)
        redmine.fail = True

        asyncio.run(issue_tab._on_page_forward(state))
        asyncio.run(issue_tab._on_page_forward(state))

        assert redmine.requested == [3, 3]
        assert state.issue_tab.offset == 0
        assert state.issue_tab.issues == _issues(1, 2, 3)
        assert state.flash_message == messages.tui_flash_fetch_failed.format(
            error="boom"
        )

    def test_stays_when_the_next_page_turned_out_empty(self, monkeypatch):
        """総数が減って送り先が空になっていたら今のページに留まり、次のページ送りは今のページから数える"""
        redmine = _FakeRedmine(monkeypatch, total=6)
        state = _state_showing(redmine, offset=0, page_size=3)
        redmine.total = 3

        asyncio.run(issue_tab._on_page_forward(state))
        asyncio.run(issue_tab._on_page_backward(state))

        assert redmine.requested == [3]
        assert state.issue_tab.offset == 0
        assert state.issue_tab.issues == _issues(1, 2, 3)

    def test_reload_while_paging_reloads_the_requested_page(self, monkeypatch):
        """ページ送りの取得中に再読込すると、送り先のページを読み込む"""
        redmine = _FakeRedmine(monkeypatch, total=9)
        state = _state_showing(redmine, offset=0, page_size=3)
        hold = redmine.hold(3)

        async def scenario():
            paging = asyncio.create_task(issue_tab._on_page_forward(state))
            await hold.wait_started()
            await issue_tab._on_reload(state)
            hold.release()
            await paging

        asyncio.run(scenario())

        assert redmine.requested == [3, 3]
        assert state.issue_tab.offset == 3
        assert state.issue_tab.issues == _issues(4, 5, 6)
