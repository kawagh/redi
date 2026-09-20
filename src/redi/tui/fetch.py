"""TUI を止めずに API を取得するための共通の入口。"""

import asyncio
from collections.abc import Callable

import requests
from prompt_toolkit.application import get_app

from redi.tui.state import TuiState


async def run_fetch[T](
    state: TuiState,
    fetch: Callable[[], T],
    apply: Callable[[T], None],
    on_error: Callable[[requests.exceptions.RequestException], None],
) -> bool:
    """`fetch` をワーカースレッドで実行し、結果を `apply` で state に反映する。

    反映したら True。取得中も描画とキー入力は止まらない。

    - `fetch` はワーカースレッドで走るので state に触れず、取得結果を返すだけにする。
      取得条件は呼び出し側がイベントループ上で読み取って束縛しておく
    - `apply` と `on_error` はイベントループ上で呼ぶので state を書き換えてよい
    - 取得中でも次の取得を受け付ける。後の操作に追い越された取得の結果は捨てる
      (最後の操作が勝つ)
    - バックグラウンドタスクは例外を漏らせないので、通信の失敗は `on_error` に渡す
    """
    generation = state.fetches.begin()
    # await の前に変えた state (取得中の表示など) を先に描かせる
    get_app().invalidate()
    is_current = False
    try:
        try:
            result = await asyncio.to_thread(fetch)
        finally:
            # TUI の終了でタスクがキャンセルされたときも取得中のままにしない
            is_current = state.fetches.finish(generation)
    except requests.exceptions.RequestException as e:
        if is_current:
            on_error(e)
        return False
    if not is_current:
        return False
    apply(result)
    return True
