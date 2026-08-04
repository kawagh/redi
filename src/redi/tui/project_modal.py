"""p で開くプロジェクト切替 modal のレイアウトと描画。"""

from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import FilterOrBool
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

from redi.i18n import messages
from redi.tui.state import Renderable, TuiState


def render_project_list(state: TuiState) -> Renderable:
    """プロジェクト切替 modal の選択肢を描画する。

    ヒントは別 Window に置くのでここには含めない。1 行目から選択肢が並ぶため、
    カーソル行はそのまま `modal.cursor` になる。
    """
    modal = state.project_modal
    parts: Renderable = []
    for i, (pid, label) in enumerate(modal.choices):
        is_cursor = i == modal.cursor
        is_active = modal.active_id is not None and pid == modal.active_id
        cursor_mark = ">" if is_cursor else " "
        active_mark = "*" if is_active else " "
        line_style = "reverse" if is_cursor else ("bold" if is_active else "")
        parts.append((line_style, f" {cursor_mark} {active_mark} {label}\n"))
    return parts


def render_project_hint() -> Renderable:
    return [("", messages.tui_project_modal_hint)]


def build_project_float(state: TuiState, show: FilterOrBool) -> Float:
    """プロジェクト切替 modal の Float を組み立てる。

    プロジェクト数が多いと選択肢が端末高を超えるため、`get_cursor_position` を
    渡してカーソル行が画面内に収まるようスクロールさせる。ヒントは選択肢とは
    別の Window に置き、スクロールしても常に見せる。

    Frame を VSplit で挟んで左右に幅1の空白パディングを置く理由は
    `run_issue_tui` の help_float 手前のコメントを参照。
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
                                        lambda: render_project_list(state),
                                        show_cursor=False,
                                        get_cursor_position=lambda: Point(
                                            0, state.project_modal.cursor
                                        ),
                                    ),
                                    wrap_lines=False,
                                    scroll_offsets=ScrollOffsets(top=1, bottom=1),
                                ),
                                # ヒントはスクロール対象から外して常に見せる
                                Window(
                                    FormattedTextControl(
                                        render_project_hint, show_cursor=False
                                    ),
                                    height=1,
                                ),
                            ]
                        ),
                        title=messages.tui_project_modal_title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=show,
        ),
    )
