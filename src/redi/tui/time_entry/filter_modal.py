"""time_entries タブの f で開くフィルタ modal のレイアウトと描画。"""

from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame

from redi.i18n import messages
from redi.tui.state import Renderable, TuiState


def render_filter_modal(state: TuiState) -> Renderable:
    f = state.time_entry_tab.filter
    modal = state.time_entry_tab.filter_modal
    parts: Renderable = [("bold fg:ansicyan", f"[{messages.tui_filter_user}]\n")]
    for i, (api_val, label) in enumerate(modal.user_choices):
        is_cursor = i == modal.user_cursor
        is_active = api_val == f.user_id
        cursor_mark = ">" if is_cursor else " "
        active_mark = "*" if is_active else " "
        line_style = "reverse" if is_cursor else ("bold" if is_active else "")
        parts.append((line_style, f" {cursor_mark} {active_mark} {label}\n"))
    parts.append(("", messages.tui_filter_hint_single))
    return parts


def build_filter_float(state: TuiState, show: FilterOrBool) -> Float:
    """time_entries タブのフィルタ modal の Float を組み立てる。

    Frame を VSplit で挟んで左右に幅1の空白パディングを置く理由は
    `run_issue_tui` の help_float 手前のコメントを参照。
    """
    return Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        Window(
                            FormattedTextControl(
                                lambda: render_filter_modal(state),
                                show_cursor=False,
                            ),
                            wrap_lines=False,
                        ),
                        title=messages.tui_filter_title_time_entries,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=show,
        ),
    )
