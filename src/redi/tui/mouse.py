"""マウス操作 (ホイール / クリック) の受け口。

prompt_toolkit の `Window` はホイールを自前の `vertical_scroll` で処理するが、
プレビューは `wrap_lines=True` の制約から `state.preview_scroll` で先頭を切る
自前スクロールをしている (`app_render._skip_lines`)。両方が動くと表示が
二重にずれるので、`Window` に渡す前にここで握って `scroll_preview` に流す。

タブ行のクリックはラベルごとに対象が違うので、ペイン全体を受ける
`WheelControl` ではなく、描画フラグメントに付けるハンドラで受ける
(`app_render.render_tabs` の `on_click`)。
"""

from collections.abc import Callable

from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

from redi.tui.app_render import TabMouseHandler
from redi.tui.conditions import Conditions
from redi.tui.keybindings.keybinding_actions import (
    activate_tab,
    clear_temporary_state,
    reset_preview_scroll,
    scroll_preview,
)
from redi.tui.state import TuiState, TuiTab
from redi.tui.tabs import TABS

# ホイール 1 目盛りで動かす行数。Ctrl+E / Ctrl+Y (1 行) より少し大きく、
# 半ページ (Ctrl+D / Ctrl+U) より小さい値。
WHEEL_LINES = 3

# 正: 下方向 / 負: 上方向 の目盛り数を受け取る。
WheelHandler = Callable[[int], None]


class WheelControl(FormattedTextControl):
    """ホイールだけを `on_wheel` に流し、他のマウスイベントは無視する FormattedTextControl。

    `on_wheel` が None のときはホイールを握りつぶす (Window の既定処理へ渡さない)。
    """

    def __init__(
        self,
        text: AnyFormattedText,
        *,
        on_wheel: WheelHandler | None = None,
        **kwargs,
    ) -> None:
        super().__init__(text, **kwargs)
        self._on_wheel = on_wheel

    def mouse_handler(self, mouse_event: MouseEvent):
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            direction = 1
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            direction = -1
        else:
            return NotImplemented
        if self._on_wheel is not None:
            self._on_wheel(direction)
        return None


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


def build_tab_click_handler(state: TuiState, conditions: Conditions) -> TabMouseHandler:
    """タブ行のラベルのクリックを Tab キーと同じタブ切り替えに変換する。

    クリックは MOUSE_UP で受ける (prompt_toolkit の Button と同じ流儀)。
    通常モードだけで効き、今のタブをクリックしても再読込はしない。
    """

    def for_tab(tab: TuiTab) -> Callable[[MouseEvent], object]:
        def on_mouse(mouse_event: MouseEvent) -> object:
            if mouse_event.event_type != MouseEventType.MOUSE_UP:
                return NotImplemented
            if not conditions.normal() or state.tab == tab:
                return NotImplemented
            activate_tab(state, tab)
            return None

        return on_mouse

    return for_tab
