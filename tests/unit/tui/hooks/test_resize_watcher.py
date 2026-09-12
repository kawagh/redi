"""端末リサイズ追従 (ResizeWatcher) の単体テスト。

prompt_toolkit への依存は全て注入されるので、Application を起動せずに
`on_render()` を直接呼んで検証する。
"""

import asyncio
from dataclasses import replace

import requests

from redi.tui.hooks import resize_watcher
from redi.tui.hooks.resize_watcher import ResizeWatcher
from redi.tui.state import TuiState, compute_page_size
from redi.tui.tabs import TABS


class _FakeTask:
    """`schedule` が返すハンドルの代役。コルーチンは走らせずに閉じる。"""

    def __init__(self, coro):
        self.cancelled = False
        coro.close()

    def cancel(self) -> None:
        self.cancelled = True


class _Harness:
    """ResizeWatcher とその周辺 (端末行数・modal 状態・予約) をまとめて操作する。"""

    def __init__(self, state: TuiState, rows: int = 30, ready: bool = True):
        self.state = state
        self.rows = rows
        self.ready = ready
        self.tasks: list[_FakeTask] = []
        self.invalidated = 0
        self.watcher = ResizeWatcher(
            state,
            get_rows=lambda: self.rows,
            is_ready=lambda: self.ready,
            schedule=self._schedule,
            invalidate=self._invalidate,
            delay=0,
        )

    def _schedule(self, coro) -> _FakeTask:
        task = _FakeTask(coro)
        self.tasks.append(task)
        return task

    def _invalidate(self) -> None:
        self.invalidated += 1

    def render(self, rows: int | None = None) -> None:
        if rows is not None:
            self.rows = rows
        self.watcher.on_render()

    @property
    def live_tasks(self) -> list[_FakeTask]:
        return [t for t in self.tasks if not t.cancelled]


def _state(tab="issues", page_size=27) -> TuiState:
    state = TuiState()
    state.tab = tab
    state.page_size = page_size
    return state


class TestPageSizeFollowsTerminal:
    """リサイズしたら page_size を即時に更新する"""

    def test_updates_page_size_without_waiting_for_refetch(self):
        """再取得を待たずに page_size が新しい値になる

        c-d / c-u の半ページスクロールは API を伴わないので、デバウンスを
        待たずに新しい画面サイズへ追従させる。
        """
        harness = _Harness(_state(), rows=30)
        harness.render()

        harness.render(rows=13)

        assert harness.state.page_size == compute_page_size(13)

    def test_does_not_schedule_when_page_size_is_unchanged(self):
        """行数が変わっても page_size が同じなら再取得を予約しない"""
        state = _state()
        harness = _Harness(state, rows=30)
        harness.render()
        assert harness.tasks == []

        harness.render(rows=30)

        assert harness.tasks == []

    def test_does_not_refetch_when_startup_size_matches(self):
        """起動時に決めた page_size と同じなら初回描画で再取得しない"""
        state = _state(page_size=compute_page_size(30))
        harness = _Harness(state, rows=30)

        harness.render()

        assert harness.tasks == []

    def test_refetches_when_startup_size_differs(self):
        """起動時の page_size と実サイズがずれていれば初回描画で取り直す"""
        state = _state(page_size=5)
        harness = _Harness(state, rows=30)

        harness.render()

        assert len(harness.live_tasks) == 1
        assert state.page_size == compute_page_size(30)


class TestDebounce:
    """連続したリサイズは 1 回の再取得に収束する"""

    def test_consecutive_resizes_keep_only_the_last_task(self):
        """リサイズを続けている間は前の待機を取り消し、生き残る予約は 1 つだけ"""
        harness = _Harness(_state(), rows=30)
        harness.render()

        harness.render(rows=25)
        harness.render(rows=20)
        harness.render(rows=15)

        assert len(harness.tasks) == 3
        assert len(harness.live_tasks) == 1
        assert harness.live_tasks[0] is harness.tasks[-1]

    def test_render_without_resize_does_not_reschedule(self):
        """リサイズを伴わない再描画では待機を張り直さない"""
        harness = _Harness(_state(), rows=30)
        harness.render()
        harness.render(rows=20)
        scheduled = len(harness.tasks)

        harness.render()

        assert len(harness.tasks) == scheduled


class TestModalSuspendsRefetch:
    """modal 表示中は再取得を保留する"""

    def test_no_refetch_while_modal_is_open(self):
        """modal 中は page_size だけ更新し、一覧の取り直しは予約しない

        y/N の削除確認中に一覧が入れ替わると、確定時に別の行を消してしまうため。
        """
        state = _state()
        harness = _Harness(state, rows=30)
        harness.render()
        harness.ready = False

        harness.render(rows=15)

        assert state.page_size == compute_page_size(15)
        assert harness.tasks == []

    def test_modal_opened_during_wait_skips_reload(self, monkeypatch):
        """予約後の待機中に modal が開いたら発火時に取り直さない

        予約時のガードだけでは 0.3 秒の待機中に開いた y/N 確認をすり抜け、
        確定時に別の行を消してしまう。タブは stale のまま残り、modal を
        閉じた後の描画で予約し直す。
        """
        called = []
        monkeypatch.setitem(
            resize_watcher.TABS, "issues", _tab_stub(lambda state: called.append(state))
        )
        harness = _Harness(_state(), rows=30)
        harness.render()
        harness.render(rows=15)
        harness.ready = False

        asyncio.run(harness.watcher._debounced_reload())

        assert called == []
        assert harness.invalidated == 0

        harness.ready = True
        scheduled = len(harness.tasks)
        harness.render()
        assert len(harness.tasks) == scheduled + 1

    def test_refetches_after_modal_closes(self):
        """modal を閉じた後の再描画で取り直しを予約する"""
        harness = _Harness(_state(), rows=30)
        harness.render()
        harness.ready = False
        harness.render(rows=15)

        harness.ready = True
        harness.render()

        assert len(harness.live_tasks) == 1


class TestReloadNow:
    """再取得は表示中のタブに対してだけ行う"""

    def test_calls_on_resize_of_active_tab(self, monkeypatch):
        """アクティブなタブの on_resize() を呼ぶ"""
        called = []
        monkeypatch.setitem(
            resize_watcher.TABS,
            "issues",
            _tab_stub(lambda state: called.append(state)),
        )
        harness = _Harness(_state(), rows=30)
        harness.render()
        harness.render(rows=15)

        harness.watcher.reload_now()

        assert called == [harness.state]

    def test_wiki_tab_is_never_refetched(self):
        """wiki タブは全件ロードなのでリサイズしても取り直さない"""
        harness = _Harness(_state(tab="wiki"), rows=30)
        harness.render()

        harness.render(rows=15)

        assert harness.tasks == []

    def test_switching_back_to_paged_tab_refetches_once(self):
        """wiki でリサイズしてから issues に戻ると、そこで 1 回だけ取り直す"""
        state = _state(tab="wiki")
        harness = _Harness(state, rows=30)
        harness.render()
        harness.render(rows=15)
        assert harness.tasks == []

        state.tab = "issues"
        harness.render()

        assert len(harness.live_tasks) == 1

    def test_request_error_shows_flash_and_keeps_list(self, monkeypatch):
        """再取得が失敗したら flash に出すだけで、一覧はそのまま残す"""

        def fail(state):
            raise requests.exceptions.ConnectionError("boom")

        monkeypatch.setitem(resize_watcher.TABS, "issues", _tab_stub(fail))
        harness = _Harness(_state(), rows=30)
        harness.render()
        harness.render(rows=15)

        harness.watcher.reload_now()

        assert harness.state.flash_message is not None
        assert "boom" in harness.state.flash_message

    def test_failure_does_not_retry_until_next_resize(self, monkeypatch):
        """失敗した後の再描画では取り直しを予約し直さない (リトライし続けない)"""

        def fail(state):
            raise requests.exceptions.ConnectionError("boom")

        monkeypatch.setitem(resize_watcher.TABS, "issues", _tab_stub(fail))
        harness = _Harness(_state(), rows=30)
        harness.render()
        harness.render(rows=15)
        harness.watcher.reload_now()
        scheduled = len(harness.tasks)

        harness.render()

        assert len(harness.tasks) == scheduled


class TestDebouncedReloadCoroutine:
    """待機コルーチンは待ってから 1 回だけ取り直す"""

    def test_reloads_and_invalidates_after_delay(self, monkeypatch):
        """待機が明けたら取り直して再描画を要求する"""
        called = []
        monkeypatch.setitem(
            resize_watcher.TABS, "issues", _tab_stub(lambda state: called.append(state))
        )
        harness = _Harness(_state(), rows=30)
        harness.render()
        harness.render(rows=15)

        asyncio.run(harness.watcher._debounced_reload())

        assert len(called) == 1
        assert harness.invalidated == 1

    def test_cancel_before_delay_skips_reload(self, monkeypatch):
        """待機中に取り消されたら取り直さない"""
        called = []
        monkeypatch.setitem(
            resize_watcher.TABS, "issues", _tab_stub(lambda state: called.append(state))
        )
        harness = _Harness(_state(), rows=30)
        harness.watcher._delay = 10
        harness.render()
        harness.render(rows=15)

        async def _run():
            task = asyncio.create_task(harness.watcher._debounced_reload())
            await asyncio.sleep(0)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(_run())

        assert called == []
        assert harness.invalidated == 0


def _tab_stub(on_resize):
    """on_resize だけ差し替えた TabView の代役。"""
    return replace(TABS["issues"], on_resize=on_resize)
