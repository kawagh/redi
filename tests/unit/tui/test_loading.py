"""API 取得中のスピナー (redi.tui.loading) の単体テスト。"""

import asyncio
import threading
from typing import Any, cast

import pytest
from prompt_toolkit.application import Application

from redi.tui.loading import SPINNER_FRAMES, run_with_spinner, spinner_frame
from redi.tui.state import TuiState


class FakeApp:
    """再描画の要求回数だけ数える Application のスタブ。"""

    def __init__(self) -> None:
        self.invalidated = 0

    def invalidate(self) -> None:
        self.invalidated += 1


def _app() -> Application[Any]:
    return cast(Application[Any], FakeApp())


class TestSpinnerFrame:
    """spinner_frame() は駒を巡回して返す"""

    def test_wraps_around(self):
        """frame が駒数を超えても先頭に戻る"""
        state = TuiState()
        state.loading.frame = len(SPINNER_FRAMES)

        assert spinner_frame(state) == SPINNER_FRAMES[0]


class TestRunWithSpinner:
    """run_with_spinner() は取得している間だけ待ち表示を立てる"""

    def test_marks_target_while_fetching(self):
        """取得関数の実行中は target と label が立っている"""
        state = TuiState()
        seen: dict[str, object] = {}

        def fetch() -> str:
            seen["target"] = state.loading.target
            seen["label"] = state.loading.label
            return "done"

        result = asyncio.run(
            run_with_spinner(state, _app(), "list", "読み込み中", fetch)
        )

        assert result == "done"
        assert seen["target"] == "list"
        assert seen["label"] == "読み込み中"

    def test_clears_target_after_fetching(self):
        """取得が終われば待ち表示は倒れる (以降は通常の描画に戻る)"""
        state = TuiState()

        asyncio.run(run_with_spinner(state, _app(), "list", "読み込み中", lambda: None))

        assert state.loading.is_active() is False
        assert state.loading.label == ""

    def test_clears_target_when_fetch_raises(self):
        """取得が失敗しても待ち表示は倒す (スピナーが回りっぱなしにならない)"""
        state = TuiState()

        def fetch() -> None:
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            asyncio.run(run_with_spinner(state, _app(), "list", "読み込み中", fetch))

        assert state.loading.is_active() is False

    def test_runs_fetch_outside_the_event_loop(self):
        """取得はイベントループとは別のスレッドで走る

        同じスレッドで走ると描画が止まり、スピナーが回らない。
        """
        state = TuiState()
        seen: dict[str, int] = {}

        async def main() -> None:
            seen["loop"] = threading.get_ident()
            await run_with_spinner(
                state,
                _app(),
                "list",
                "読み込み中",
                lambda: seen.__setitem__("fetch", threading.get_ident()),
            )

        asyncio.run(main())

        assert seen["fetch"] != seen["loop"]
