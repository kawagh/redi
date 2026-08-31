"""端末リサイズに追従して page_size を更新し、一覧を取り直す。

prompt_toolkit は SIGWINCH とサイズのポーリングの 2 経路で再描画するので、
`after_render` を 1 本フックすれば両方拾える。サイズが動いている間は API を
叩かず、止まってから 1 回だけ取り直す (デバウンス)。
"""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, Protocol

import requests
from prompt_toolkit import Application

from redi.i18n import messages
from redi.tui.conditions import Conditions
from redi.tui.state import TuiState, TuiTab
from redi.tui.tab import noop
from redi.tui.tabs import TABS

# サイズが止まったと見なすまでの待ち時間 (秒)。
DEBOUNCE_SECONDS = 0.3

# page_size に応じてサーバーから 1 ページ分だけ取るタブ。
# ページングしないタブ (wiki) は on_resize が noop なのでそこから導く。
PAGED_TABS: frozenset[TuiTab] = frozenset(
    tab for tab, view in TABS.items() if view.on_resize is not noop
)


class _Cancellable(Protocol):
    def cancel(self) -> Any: ...


class ResizeWatcher:
    """描画のたびに端末サイズを見て page_size と一覧を追従させる。

    prompt_toolkit に依存する部分は全て呼び出し側から関数で受け取るので、
    テストでは Application を起動せずに `on_render()` を直接呼べる。
    """

    def __init__(
        self,
        state: TuiState,
        *,
        get_rows: Callable[[], int],
        is_ready: Callable[[], bool],
        schedule: Callable[[Coroutine[Any, Any, None]], _Cancellable],
        invalidate: Callable[[], None],
        delay: float = DEBOUNCE_SECONDS,
    ) -> None:
        self._state = state
        self._get_rows = get_rows
        self._is_ready = is_ready
        self._schedule = schedule
        self._invalidate = invalidate
        self._delay = delay
        # page_size が変わったまま取り直していないタブ。
        self._stale_tabs: set[TuiTab] = set()
        self._scheduled_task: _Cancellable | None = None

    def on_render(self) -> None:
        """描画のたびに呼ばれ、page_size の更新と再取得の予約だけを行う。

        描画中に一覧を差し替えると表示が壊れるため、ここで書き換えるのは
        page_size と _stale_tabs / _scheduled_task のみ。取得は必ず _debounced_reload の中で行う。
        """
        resized = self._state.apply_terminal_rows(self._get_rows())
        if resized:
            self._stale_tabs = set(PAGED_TABS)
        if self._state.tab not in self._stale_tabs or not self._is_ready():
            return
        # resized: サイズが動いている間は待ち直す (デバウンス)
        # _scheduled_task is None: modal を閉じた / タブを切り替えた等で今から待ち始める
        if resized or self._scheduled_task is None:
            self._restart()

    def _restart(self) -> None:
        self._cancel_scheduled_task()
        self._scheduled_task = self._schedule(self._debounced_reload())

    def _cancel_scheduled_task(self) -> None:
        if self._scheduled_task is not None:
            self._scheduled_task.cancel()
            self._scheduled_task = None

    async def _debounced_reload(self) -> None:
        await asyncio.sleep(self._delay)
        self._scheduled_task = None
        # 待機中に modal が開いた場合は差し替えない (予約時のガードだけでは
        # すり抜ける)。タブは _stale_tabs に残るので、modal を閉じた後の
        # 描画で予約し直される。
        if not self._is_ready():
            return
        self.reload_now()
        self._invalidate()

    def reload_now(self) -> None:
        """現在のタブを新しい page_size で取り直す。失敗しても一覧は保持する。"""
        tab = self._state.tab
        # 成否によらず stale から降ろす。失敗のたびに再描画 → 再予約を繰り返して
        # リトライし続けるのを避ける (次のリサイズまで待つ)。
        self._stale_tabs.discard(tab)
        try:
            TABS[tab].on_resize(self._state)
        except requests.exceptions.RequestException as e:
            self._state.flash_message = messages.tui_flash_resize_reload_failed.format(
                error=e
            )


def attach_resize_watcher(
    app: Application,
    state: TuiState,
    conditions: Conditions,
) -> ResizeWatcher:
    """描画のたびに端末サイズを確認するフックを登録する。"""
    watcher = ResizeWatcher(
        state,
        get_rows=lambda: app.output.get_size().rows,
        is_ready=lambda: not app.is_done and conditions.normal(),
        schedule=app.create_background_task,
        invalidate=app.invalidate,
    )

    def _on_after_render(sender: Application) -> None:
        watcher.on_render()

    app.after_render += _on_after_render
    return watcher
