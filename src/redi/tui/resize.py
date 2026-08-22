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
from redi.tui.tabs import TABS

# サイズが止まったと見なすまでの待ち時間 (秒)。
DEBOUNCE_SECONDS = 0.3

# page_size に応じてサーバーから 1 ページ分だけ取るタブ。
# wiki は全件ロードなので対象外。
PAGED_TABS: frozenset[TuiTab] = frozenset({"issues", "time_entries"})


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
        self._last_rows: int | None = None
        # page_size が変わったまま取り直していないタブ。
        self._stale: set[TuiTab] = set()
        self._pending: _Cancellable | None = None

    def on_render(self) -> None:
        """描画のたびに呼ばれ、page_size の更新と再取得の予約だけを行う。

        描画中に一覧を差し替えると表示が壊れるため、ここで書き換えるのは
        page_size とブックキーピングのみ。取得は必ず待機タスクの中で行う。
        """
        rows = self._get_rows()
        resized = rows != self._last_rows
        if resized:
            self._last_rows = rows
            if self._state.apply_terminal_rows(rows):
                self._stale = set(PAGED_TABS)
            else:
                # 行数は動いたが page_size は変わらなかった (上限や下限に丸められた)。
                resized = False
        if self._state.tab not in self._stale or not self._is_ready():
            return
        # resized: サイズが動いている間は待ち直す (デバウンス)
        # _pending is None: modal を閉じた / タブを切り替えた等で今から待ち始める
        if resized or self._pending is None:
            self._restart()

    def _restart(self) -> None:
        self._cancel_pending()
        self._pending = self._schedule(self._debounced_reload())

    def _cancel_pending(self) -> None:
        if self._pending is not None:
            self._pending.cancel()
            self._pending = None

    async def _debounced_reload(self) -> None:
        await asyncio.sleep(self._delay)
        self._pending = None
        self.reload_now()
        self._invalidate()

    def reload_now(self) -> None:
        """現在のタブを新しい page_size で取り直す。失敗しても一覧は保持する。"""
        tab = self._state.tab
        # 成否によらず stale から降ろす。失敗のたびに再描画 → 再予約を繰り返して
        # リトライし続けるのを避ける (次のリサイズまで待つ)。
        self._stale.discard(tab)
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
    delay: float = DEBOUNCE_SECONDS,
) -> ResizeWatcher:
    """描画のたびに端末サイズを確認するフックを登録する。"""
    watcher = ResizeWatcher(
        state,
        get_rows=lambda: app.output.get_size().rows,
        is_ready=lambda: not app.is_done and conditions.normal(),
        schedule=app.create_background_task,
        invalidate=app.invalidate,
        delay=delay,
    )

    def _on_after_render(sender: Application) -> None:
        watcher.on_render()

    app.after_render += _on_after_render
    return watcher
