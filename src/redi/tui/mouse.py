"""マウス操作 (ホイール / クリック) を受ける部品。

ペインの矩形全体でマウスイベントを受ける `PaneControl` と、ハンドラの型を
置く。どのペインで何をするかはここでは決めず、各ペイン (`panes/`) が
自分の Window と一緒にハンドラを定義する。
"""

from collections.abc import Callable

from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

# 正: 下方向 / 負: 上方向 の目盛り数を受け取る。
WheelHandler = Callable[[int], None]
# クリックした位置をコントロール内の (桁, 行) で受け取る。行はスクロール分を
# prompt_toolkit が補正した後の値なので、1 行 1 項目の一覧ではそのまま添字になる。
ClickHandler = Callable[[Point], None]


class PaneControl(FormattedTextControl):
    """一覧・プレビューのペインに使う FormattedTextControl。

    ペインの矩形全体 (空行や余白を含む) でマウスイベントを受け、ホイールを
    `on_wheel` に、クリック (MOUSE_UP) をクリック位置と共に `on_click` に流す。
    他のイベントは無視する。
    `on_wheel` が None のときはホイールを握りつぶす (Window の既定処理へ渡さない)。
    `on_click` が None のときはクリックを未処理として返す。
    """

    def __init__(
        self,
        text: AnyFormattedText,
        *,
        on_wheel: WheelHandler | None = None,
        on_click: ClickHandler | None = None,
        **kwargs,
    ) -> None:
        super().__init__(text, **kwargs)
        self._on_wheel = on_wheel
        self._on_click = on_click

    def mouse_handler(self, mouse_event: MouseEvent):
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            direction = 1
        elif mouse_event.event_type == MouseEventType.SCROLL_UP:
            direction = -1
        elif mouse_event.event_type == MouseEventType.MOUSE_UP:
            if self._on_click is None:
                return NotImplemented
            self._on_click(mouse_event.position)
            return None
        else:
            return NotImplemented
        if self._on_wheel is not None:
            self._on_wheel(direction)
        return None
