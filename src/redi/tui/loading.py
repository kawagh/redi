"""API 取得を待っている間のスピナー。

タブのデータ取得はいずれも同期呼び出しなので、キーバインドからそのまま呼ぶと
prompt_toolkit のイベントループごと止まり、待ちの表示が出せない (既存の
「読み込み中...」が実際にはほぼ見えないのはこのため)。ここで取得をワーカー
スレッドへ逃がし、待っている間だけ一定間隔で `invalidate()` して駒を進める。
"""

import asyncio
from collections.abc import Callable
from typing import Any

from prompt_toolkit.application import Application

from redi.tui.state import LoadingTarget, TuiState

# スピナーの駒。braille は表示幅 1 セルなので CJK 混在でも桁がずれない。
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# 駒を進める間隔 (秒)。
FRAME_INTERVAL = 0.1


def spinner_frame(state: TuiState) -> str:
    return SPINNER_FRAMES[state.loading.frame % len(SPINNER_FRAMES)]


async def _animate(state: TuiState, app: Application[Any]) -> None:
    """取得が終わって cancel されるまで駒を進め続ける。"""
    while True:
        app.invalidate()
        await asyncio.sleep(FRAME_INTERVAL)
        state.loading.frame += 1


async def run_with_spinner[T](
    state: TuiState,
    app: Application[Any],
    target: LoadingTarget,
    label: str,
    fn: Callable[[], T],
) -> T:
    """`fn` を別スレッドで実行し、その間 `target` の領域にスピナーを出す。

    `fn` が投げた例外はそのまま呼び出し元へ伝える。待ち表示の後始末は
    成功・失敗のどちらでも行う。
    """
    state.loading.target = target
    state.loading.label = label
    state.loading.frame = 0
    animation = asyncio.create_task(_animate(state, app))
    try:
        return await asyncio.to_thread(fn)
    finally:
        animation.cancel()
        state.loading.target = None
        state.loading.label = ""
        app.invalidate()
