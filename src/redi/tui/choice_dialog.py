"""一覧から1つ選ぶダイアログの共通部品。

p のプロジェクト切替と P のプロファイル切替は、選択肢の作り方と決定時の処理だけが
違って描画とキー操作は同じなので、ここに寄せる。
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
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame

from redi.tui.state import ChoiceDialogState, Renderable

GetDialog = Callable[[], ChoiceDialogState]


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


def build_choice_dialog(
    get_dialog: GetDialog, title: str, hint: str, show: FilterOrBool
) -> Float:
    """選択肢ダイアログの Float を組み立てる。

    選択肢が端末高を超えることがあるため、`get_cursor_position` を渡してカーソル行が
    画面内に収まるようスクロールさせる。ヒントは選択肢とは別の Window に置き、
    スクロールしても常に見せる。

    Frame を VSplit で挟んで左右に幅1の空白パディングを置く理由は
    `run_issue_tui` の help_dialog 手前のコメントを参照。
    """
    return Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        HSplit(
                            [
                                Window(
                                    FormattedTextControl(
                                        lambda: render_choice_list(get_dialog()),
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
                                    FormattedTextControl(hint, show_cursor=False),
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
    on_enter: Callable[..., None],
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
        dialog = get_dialog()
        dialog.cursor = min(len(dialog.choices) - 1, dialog.cursor + 1)

    @kb.add("k", filter=show)
    @kb.add("up", filter=show)
    @kb.add("c-p", filter=show)
    def _cursor_up(event):
        dialog = get_dialog()
        dialog.cursor = max(0, dialog.cursor - 1)

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
        if not dialog.choices:
            return
        value, label = dialog.choices[dialog.cursor]
        on_enter(event, value, label)

    @kb.add("escape", filter=show)
    @kb.add(close_key, filter=show)
    @kb.add("q", filter=show)
    def _close(event):
        get_dialog().show = False
