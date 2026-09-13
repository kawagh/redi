"""一覧から1つ選ぶダイアログの共通部品。

p のプロジェクト切替と P のプロファイル切替、wiki の h の版一覧は、選択肢の作り方と
決定時の処理だけが違って描画とキー・マウス操作は同じなので、ここに寄せる。
"""

from collections.abc import Callable

from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    HSplit,
    ScrollOffsets,
    VSplit,
    Window,
)
from prompt_toolkit.widgets import Frame

from redi.tui.mouse import ClickHandler, PaneControl, WheelHandler
from redi.tui.state import ChoiceDialogState, Renderable

GetDialog = Callable[[], ChoiceDialogState]
# 決定時の処理。選んだ選択肢の (値, 表示ラベル) を受け取る。
# Enter とクリックの両方から呼ぶので、キーイベントには依存しない。
SelectHandler = Callable[[str, str], None]


def render_choice_list(dialog: ChoiceDialogState) -> Renderable:
    """選択肢を描画する。

    ヒントは別 Window に置くのでここには含めない。1 行目から選択肢が並ぶため、
    カーソル行はそのまま `ダイアログ.cursor` になる。
    """
    parts: Renderable = []
    for i, (value, label) in enumerate(dialog.choices):
        is_cursor = i == dialog.cursor
        is_active = dialog.active_value is not None and value == dialog.active_value
        cursor_mark = ">" if is_cursor else " "
        active_mark = "*" if is_active else " "
        line_style = "reverse" if is_cursor else ("bold" if is_active else "")
        parts.append((line_style, f" {cursor_mark} {active_mark} {label}\n"))
    return parts


def move_cursor(dialog: ChoiceDialogState, delta: int) -> None:
    """カーソルを `delta` 行動かす。先頭・末尾で止まる。"""
    last = max(0, len(dialog.choices) - 1)
    dialog.cursor = min(last, max(0, dialog.cursor + delta))


def select_choice(
    dialog: ChoiceDialogState, index: int, on_select: SelectHandler
) -> None:
    """`index` の選択肢にカーソルを合わせて決定する。範囲外なら何もしない。"""
    if not 0 <= index < len(dialog.choices):
        return
    dialog.cursor = index
    value, label = dialog.choices[index]
    on_select(value, label)


def build_choice_wheel_handler(get_dialog: GetDialog) -> WheelHandler:
    """ダイアログ上のホイールを j / k と同じ 1 行のカーソル移動に変換する。

    一覧ペインと同じく Window 既定のスクロールには渡さない。渡すとカーソル行の
    追従 (`get_cursor_position`) と表示がずれる。
    """

    def on_wheel(direction: int) -> None:
        move_cursor(get_dialog(), 1 if direction > 0 else -1)

    return on_wheel


def build_choice_click_handler(
    get_dialog: GetDialog, on_select: SelectHandler
) -> ClickHandler:
    """選択肢の行のクリックを「その行にカーソルを合わせて Enter」に変換する。

    選択肢は 1 行 1 項目で折り返し無しなので、クリック位置の行がそのまま添字になる。
    行の右側の余白をクリックしても同じ行として受ける。選択肢の無い行 (末尾の空行)
    は無視する。
    """

    def on_click(position: Point) -> None:
        select_choice(get_dialog(), position.y, on_select)

    return on_click


def build_choice_dialog(
    get_dialog: GetDialog,
    title: str,
    hint: str,
    show: FilterOrBool,
    on_select: SelectHandler,
) -> Float:
    """選択肢ダイアログの Float を組み立てる。

    選択肢が端末高を超えることがあるため、`get_cursor_position` を渡してカーソル行が
    画面内に収まるようスクロールさせる。ヒントは選択肢とは別の Window に置き、
    スクロールしても常に見せる。

    ホイールは選択肢とヒントのどちらの上でもカーソルを動かす。クリックは選択肢の
    上でだけ決定にする。

    Frame を VSplit で挟んで左右に幅1の空白パディングを置く理由は
    `run_issue_tui` の help_dialog 手前のコメントを参照。
    """
    on_wheel = build_choice_wheel_handler(get_dialog)
    return Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        HSplit(
                            [
                                Window(
                                    PaneControl(
                                        lambda: render_choice_list(get_dialog()),
                                        on_wheel=on_wheel,
                                        on_click=build_choice_click_handler(
                                            get_dialog, on_select
                                        ),
                                        show_cursor=False,
                                        get_cursor_position=lambda: Point(
                                            0, get_dialog().cursor
                                        ),
                                    ),
                                    wrap_lines=False,
                                    scroll_offsets=ScrollOffsets(top=1, bottom=1),
                                ),
                                # ヒントはスクロール対象から外して常に見せる
                                Window(
                                    PaneControl(
                                        hint, on_wheel=on_wheel, show_cursor=False
                                    ),
                                    height=1,
                                ),
                            ]
                        ),
                        title=title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=show,
        ),
    )


def register_choice_keys(
    kb: KeyBindings,
    get_dialog: GetDialog,
    show: FilterOrBool,
    close_key: str,
    on_select: SelectHandler,
) -> None:
    """選択肢ダイアログの移動・決定・閉じるキーを登録する。

    `close_key` はダイアログを開いたキー自身 (トグルで閉じられるようにする)。

    候補は環境が増えるほど伸びるので、一覧側の normal mode と同じ `gg` / `G` で
    先頭・末尾へ飛べるようにする。
    """

    @kb.add("j", filter=show)
    @kb.add("down", filter=show)
    @kb.add("c-n", filter=show)
    def _cursor_down(event):
        move_cursor(get_dialog(), 1)

    @kb.add("k", filter=show)
    @kb.add("up", filter=show)
    @kb.add("c-p", filter=show)
    def _cursor_up(event):
        move_cursor(get_dialog(), -1)

    @kb.add("g", "g", filter=show)
    def _cursor_top(event):
        get_dialog().cursor = 0

    @kb.add("G", filter=show)
    def _cursor_bottom(event):
        dialog = get_dialog()
        dialog.cursor = max(0, len(dialog.choices) - 1)

    @kb.add("enter", filter=show)
    def _select(event):
        dialog = get_dialog()
        select_choice(dialog, dialog.cursor, on_select)

    @kb.add("escape", filter=show)
    @kb.add(close_key, filter=show)
    @kb.add("q", filter=show)
    def _close(event):
        get_dialog().show = False
