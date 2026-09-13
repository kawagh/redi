"""プレビュー (右ペイン)。ホイールによるスクロールとクリックを持つ。

prompt_toolkit の `Window` はホイールを自前の `vertical_scroll` で処理するが、
プレビューは `wrap_lines=True` の制約から `state.preview_scroll` で先頭を切る
自前スクロールをしている (`app_render._skip_lines`)。両方が動くと表示が
二重にずれるので、`Window` に渡す前に `PaneControl` で握って
`scroll_preview` に流す。
"""

from prompt_toolkit.layout.containers import Window

from redi.tui.app_render import render_preview_current
from redi.tui.conditions import Conditions
from redi.tui.keybindings.keybinding_actions import scroll_preview
from redi.tui.mouse import ClickHandler, PaneControl, WheelHandler
from redi.tui.panes import HALF
from redi.tui.state import TuiState
from redi.tui.tabs import TABS

# ホイール 1 目盛りで動かす行数。Ctrl+E / Ctrl+Y (1 行) より少し大きく、
# 半ページ (Ctrl+D / Ctrl+U) より小さい値。
WHEEL_LINES = 3


def build_preview_wheel_handler(
    state: TuiState, conditions: Conditions
) -> WheelHandler:
    """プレビュー上のホイールを Ctrl+E / Ctrl+Y と同じスクロールに変換する。

    キー操作と同じく、通常モードとコメント選択モードのときだけ効く。
    ダイアログ表示中はダイアログの外を回しても何も起きない。
    """

    def on_wheel(direction: int) -> None:
        if not (conditions.normal() or conditions.comment_select()):
            return
        scroll_preview(state, direction * WHEEL_LINES)

    return on_wheel


def build_preview_click_handler(
    state: TuiState, conditions: Conditions
) -> ClickHandler:
    """プレビューのクリックを wiki タブの Enter (本文の読み込み) に変換する。

    ひとまず wiki だけ。issue タブの Enter はコメント選択モードに入るので、
    クリックで意図せずモードが変わらないよう対象にしない。
    """

    def on_click() -> None:
        if not conditions.normal() or state.tab != "wiki":
            return
        TABS["wiki"].on_enter(state)

    return on_click


def build_preview_window(state: TuiState, conditions: Conditions) -> Window:
    """プレビューの Window。"""
    return Window(
        PaneControl(
            lambda: render_preview_current(state),
            on_wheel=build_preview_wheel_handler(state, conditions),
            on_click=build_preview_click_handler(state, conditions),
        ),
        wrap_lines=True,
        width=HALF,
    )
