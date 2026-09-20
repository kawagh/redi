"""TUI を止めずに API を取得するための共通の入口。"""

import asyncio
from collections.abc import Callable

import requests
from prompt_toolkit.application import get_app

from redi.tui.state import TuiState


async def run_fetch[T](
    state: TuiState,
    fetch: Callable[[], T],
    *,
    still_wanted: Callable[[], bool],
    apply: Callable[[T], None],
    on_error: Callable[[requests.exceptions.RequestException], None],
) -> None:
    """`fetch` をワーカースレッドで実行し、結果を `apply` で state に反映する。

    取得中も描画とキー入力は止まらない。

    - `fetch` はワーカースレッドで走るので state に触れず、取得結果を返すだけにする。
      取得条件は呼び出し側がイベントループ上で読み取って束縛しておく
    - `still_wanted` / `apply` / `on_error` はイベントループ上で呼ぶ
    - 取得中でも次の取得を受け付ける。届いた時点で画面がもうその結果を求めて
      いなければ (`still_wanted` が偽)、結果も失敗も捨てる
    - バックグラウンドタスクは例外を漏らせないので、通信の失敗は `on_error` に渡す
    """
    state.fetching += 1
    # await の前に変えた state (取得中の表示など) を先に描かせる
    get_app().invalidate()
    try:
        result = await asyncio.to_thread(fetch)
    except requests.exceptions.RequestException as e:
        if still_wanted():
            on_error(e)
        return
    finally:
        # TUI の終了でタスクがキャンセルされたときも取得中のままにしない
        state.fetching -= 1
    if still_wanted():
        apply(result)
