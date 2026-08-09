"""画面のレイアウト (Window / Float) の組み立て。"""

from prompt_toolkit.data_structures import Point
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame

from redi.i18n import messages
from redi.tui.app_render import (
    render_error_modal,
    render_help,
    render_list_current,
    render_preview_current,
    render_status,
    render_tabs,
)
from redi.tui.conditions import Conditions
from redi.tui.issue.filter_modal import build_filter_float
from redi.tui.project_modal import build_project_float
from redi.tui.state import TuiState
from redi.tui.tabs import TABS
from redi.tui.time_entry.filter_modal import (
    build_filter_float as build_time_entry_filter_float,
)


def build_layout(state: TuiState, conditions: Conditions) -> Layout:
    preview_window = Window(
        FormattedTextControl(lambda: render_preview_current(state)),
        wrap_lines=True,
    )

    main_layout = HSplit(
        [
            Window(
                FormattedTextControl(lambda: render_tabs(state), show_cursor=False),
                height=1,
            ),
            Window(height=1, char="─"),
            VSplit(
                [
                    Window(
                        FormattedTextControl(
                            lambda: render_list_current(state),
                            show_cursor=False,
                            get_cursor_position=lambda: Point(
                                0, TABS[state.tab].get_cursor_y(state)
                            ),
                        )
                    ),
                    Window(width=1, char="│"),
                    preview_window,
                ]
            ),
            Window(FormattedTextControl(lambda: render_status(state)), height=1),
        ]
    )

    # Frame を VSplit で挟んで左右に幅1の空白パディングを置く。
    # Float の真下の行が CJK 文字 (display width=2) で終わると、その2セル目と
    # Frame の左ボーダーが同じ列に重なり、prompt_toolkit のレンダラが wide
    # char の幅ぶんカーソルを進めて Frame ボーダーのセルをスキップしてしまう
    # (= 縁が表示されない)。1セルの空白を挟むとスキップ先がボーダーではなく
    # 空白セルに変わるので、ボーダーは常に描画される。
    help_float = Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        Window(
                            FormattedTextControl(
                                lambda: render_help(state), show_cursor=False
                            ),
                            wrap_lines=False,
                        ),
                        title=lambda: messages.tui_help_title.format(
                            label=TABS[state.tab].label
                        ),
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=conditions.help_modal,
        ),
    )

    filter_float = build_filter_float(state, conditions.issue_filter_modal)

    time_entry_filter_float = build_time_entry_filter_float(
        state, conditions.time_entry_filter_modal
    )

    project_float = build_project_float(state, conditions.project_modal)

    error_float = Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        Window(
                            FormattedTextControl(
                                lambda: render_error_modal(state), show_cursor=False
                            ),
                            wrap_lines=True,
                        ),
                        title=lambda: messages.tui_error_modal_title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=conditions.error_modal,
        ),
    )

    return Layout(
        FloatContainer(
            content=main_layout,
            floats=[
                help_float,
                filter_float,
                time_entry_filter_float,
                project_float,
                error_float,
            ],
        )
    )
