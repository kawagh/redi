"""マウス操作 (ホイール / クリック) を受ける部品。

ペインの矩形全体でマウスイベントを受ける `PaneControl` と、ハンドラの型を
置く。どのペインで何をするかはここでは決めず、各ペイン (`panes/`) が
自分の Window と一緒にハンドラを定義する。
"""

from collections.abc import Callable

from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.layout.controls import FormattedTextControl, UIContent
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

# 正: 下方向 / 負: 上方向 の目盛り数を受け取る。
WheelHandler = Callable[[int], None]
# クリックした位置をコントロール内の (桁, 行) で受け取る。行はスクロール分を
# prompt_toolkit が補正した後の値なので、1 行 1 項目の一覧ではそのまま添字になる。
ClickHandler = Callable[[Point], None]
# 描画のたびにペインの (幅, 高さ) を受け取る。折り返し込みで表示行を数えるときに使う。
SizeHandler = Callable[[int, int], None]


class PaneControl(FormattedTextControl):
    """一覧・プレビューのペインに使う FormattedTextControl。

    ペインの矩形全体 (空行や余白を含む) でマウスイベントを受け、ホイールを
    `on_wheel` に、クリック (MOUSE_UP) をクリック位置と共に `on_click` に流す。
    他のイベントは無視する。
    `on_wheel` が None のときはホイールを握りつぶす (Window の既定処理へ渡さない)。
    `on_click` が None のときはクリックを未処理として返す。
    `on_size` を渡すと、描画のたびにペインの実際の (幅, 高さ) を流す。
    """

    def __init__(
        self,
        text: AnyFormattedText,
        *,
        on_wheel: WheelHandler | None = None,
        on_click: ClickHandler | None = None,
        on_size: SizeHandler | None = None,
        **kwargs,
    ) -> None:
        super().__init__(text, **kwargs)
        self._on_wheel = on_wheel
        self._on_click = on_click
        self._on_size = on_size

    def create_content(self, width: int, height: int | None) -> UIContent:
        # Window が描画時に呼ぶ。幅は折り返しに使われる実際の桁数。
        if self._on_size is not None and height is not None:
            self._on_size(width, height)
        return super().create_content(width, height)

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
