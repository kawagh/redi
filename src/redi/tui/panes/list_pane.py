"""一覧 (左ペイン)。ホイールによるカーソル移動を持つ。"""

from prompt_toolkit.data_structures import Point
from prompt_toolkit.layout.containers import Window

from redi.tui.app_render import render_list_current
from redi.tui.conditions import Conditions
from redi.tui.keybindings.keybinding_actions import (
    clear_temporary_state,
    reset_preview_scroll,
)
from redi.tui.mouse import PaneControl, WheelHandler
from redi.tui.panes import HALF
from redi.tui.state import TuiState
from redi.tui.tabs import TABS


def build_list_wheel_handler(state: TuiState, conditions: Conditions) -> WheelHandler:
    """一覧上のホイールを j / k と同じカーソル移動に変換する。

    一覧はページ単位で端末に収まっているので、隠れた行をずらす「スクロール」は
    無い。代わりに 1 目盛りで 1 行カーソルを動かす。j / k と同じく通常モード
    だけで効き、プレビューのスクロール位置も先頭へ戻す。
    """

    def on_wheel(direction: int) -> None:
        if not conditions.normal():
            return
        clear_temporary_state(state)
        reset_preview_scroll(state)
        if direction > 0:
            TABS[state.tab].on_down(state)
        else:
            TABS[state.tab].on_up(state)

    return on_wheel


def build_list_window(state: TuiState, conditions: Conditions) -> Window:
    """一覧の Window。

    ホイールはカーソル移動に充てる。Window 既定の vertical_scroll に渡すと
    カーソル行の追従 (get_cursor_position) と表示がずれる。
    """
    return Window(
        PaneControl(
            lambda: render_list_current(state),
            on_wheel=build_list_wheel_handler(state, conditions),
            show_cursor=False,
            get_cursor_position=lambda: Point(0, TABS[state.tab].get_cursor_y(state)),
        ),
        width=HALF,
    )
