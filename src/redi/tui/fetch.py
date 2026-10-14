"""TUI を止めずに API を取得するための共通の入口。"""

import asyncio
from collections.abc import Callable

from prompt_toolkit.application import get_app


async def run_fetch[T](fetch: Callable[[], T]) -> T:
    """`fetch` をワーカースレッドで実行して結果を返す。取得中も描画とキー入力は止まらない。

    - `fetch` はワーカースレッドで走るので state に触れず、取得結果を返すだけにする。
      取得条件は呼び出し側がイベントループ上で読み取って束縛しておく
    - 待っている間も操作は続くので、戻った時点で結果がまだ要るかは呼び出し側が確かめる
    - バックグラウンドタスクは例外を漏らせないので、通信の失敗は呼び出し側で受ける
    """
    # await の前に変えた state (取得中の表示など) を先に描かせる
    get_app().invalidate()
    return await asyncio.to_thread(fetch)
