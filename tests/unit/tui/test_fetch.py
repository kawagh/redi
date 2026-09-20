"""TUI を止めずに API を取得する仕組み (run_fetch) の単体テスト。"""

import asyncio
import threading
from typing import cast

import requests

from redi.api.issue import Issue, IssuesPageResponse
from redi.i18n import messages
from redi.tui.issue import issue_tab
from redi.tui.state import TuiState

FETCH_WAIT_SECONDS = 5


def _issues(*ids: int) -> list[Issue]:
    return cast(list[Issue], [{"id": i, "subject": f"issue-{i}"} for i in ids])


class _BlockedFetch:
    """`release()` するまで応答が返らない取得。遅い Redmine の代わり。"""

    def __init__(self, monkeypatch, issues: list[Issue]):
        self._issues = issues
        self._started = threading.Event()
        self._released = threading.Event()
        monkeypatch.setattr(issue_tab, "issues_fetcher", lambda state, offset: self)

    def __call__(self):
        self._started.set()
        assert self._released.wait(FETCH_WAIT_SECONDS)
        return {"issues": self._issues, "total_count": len(self._issues)}

    async def wait_started(self) -> None:
        assert await asyncio.to_thread(self._started.wait, FETCH_WAIT_SECONDS)

    def release(self) -> None:
        self._released.set()


class TestIssueReloadDoesNotBlock:
    """issue タブの再読込は、応答を待つ間も TUI の操作を止めない"""

    def test_cursor_moves_while_fetching(self, monkeypatch):
        """取得中もカーソルを動かせて、結果が届いた後もその位置が保たれる"""
        state = TuiState()
        state.issue_tab.issues = _issues(1, 2, 3, 4, 5)
        fetch = _BlockedFetch(monkeypatch, _issues(1, 2, 3, 4, 5))

        async def scenario():
            reloading = asyncio.create_task(issue_tab._on_reload(state))
            await fetch.wait_started()
            assert state.fetches.is_fetching()
            assert state.flash_message == messages.tui_flash_reloading
            issue_tab.ISSUE_TAB.on_down(state)
            issue_tab.ISSUE_TAB.on_down(state)
            assert state.issue_tab.cursor == 2
            fetch.release()
            await reloading

        asyncio.run(scenario())

        assert state.issue_tab.cursor == 2
        assert not state.fetches.is_fetching()
        assert state.flash_message == messages.tui_flash_reloaded

    def test_later_reload_wins_over_the_one_in_flight(self, monkeypatch):
        """取得中に再読込を重ねると後の結果が反映され、遅れて届いた先の結果は捨てられる"""
        state = TuiState()
        slow = _BlockedFetch(monkeypatch, _issues(1, 2, 3))
        latest = _issues(7, 8)

        async def scenario():
            first = asyncio.create_task(issue_tab._on_reload(state))
            await slow.wait_started()
            monkeypatch.setattr(
                issue_tab,
                "issues_fetcher",
                lambda state, offset: lambda: {"issues": latest, "total_count": 2},
            )
            await issue_tab._on_reload(state)
            assert not state.fetches.is_fetching()
            slow.release()
            await first

        asyncio.run(scenario())

        assert state.issue_tab.issues == latest
        assert state.flash_message == messages.tui_flash_reloaded
        assert not state.fetches.is_fetching()

    def test_discards_result_when_list_was_replaced_while_fetching(self, monkeypatch):
        """取得中に別の操作で一覧が差し替わったら、後から届いた古い結果で上書きしない"""
        state = TuiState()
        state.issue_tab.issues = _issues(1, 2, 3)
        fetch = _BlockedFetch(monkeypatch, _issues(1, 2, 3))
        next_page = _issues(4, 5, 6)

        async def scenario():
            reloading = asyncio.create_task(issue_tab._on_reload(state))
            await fetch.wait_started()
            page: IssuesPageResponse = {
                "issues": next_page,
                "total_count": 6,
                "offset": 3,
                "limit": 3,
            }
            issue_tab._apply_page(state, page, 3)
            fetch.release()
            await reloading

        asyncio.run(scenario())

        assert state.issue_tab.issues == next_page
        assert state.issue_tab.offset == 3

    def test_fetch_failure_is_shown_and_keeps_the_list(self, monkeypatch):
        """取得に失敗したら通知を出し、例外は漏らさず一覧も保つ"""
        state = TuiState()
        state.issue_tab.issues = _issues(1, 2, 3)

        def failing_fetch():
            raise requests.exceptions.ConnectionError("boom")

        monkeypatch.setattr(
            issue_tab, "issues_fetcher", lambda state, offset: failing_fetch
        )

        asyncio.run(issue_tab._on_reload(state))

        assert state.issue_tab.issues == _issues(1, 2, 3)
        assert state.flash_message == messages.tui_flash_reload_failed.format(
            error="boom"
        )
        assert not state.fetches.is_fetching()
