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
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.widgets import Frame

from redi.i18n import messages
from redi.tui.app_render import (
    render_error_dialog,
    render_help,
    render_list_current,
    render_preview_current,
    render_status,
    render_tabs,
)
from redi.tui.conditions import Conditions
from redi.tui.issue.delete_dialog import build_delete_dialog
from redi.tui.issue.filter_dialog import build_filter_dialog
from redi.tui.issue.find_dialog import build_find_dialog
from redi.tui.profile_dialog import build_profile_dialog
from redi.tui.project_dialog import build_project_dialog
from redi.tui.state import TuiState
from redi.tui.tabs import TABS
from redi.tui.time_entry.filter_dialog import (
    build_filter_dialog as build_time_entry_filter_dialog,
)
from redi.tui.wiki.delete_dialog import build_delete_dialog as build_wiki_delete_dialog
from redi.tui.wiki.diff_dialog import build_diff_dialog as build_wiki_diff_dialog
from redi.tui.wiki.version_dialog import (
    build_version_dialog as build_wiki_version_dialog,
)

HALF = Dimension(weight=1, preferred=0)


def build_layout(state: TuiState, conditions: Conditions) -> Layout:
    list_window = Window(
        FormattedTextControl(
            lambda: render_list_current(state),
            show_cursor=False,
            get_cursor_position=lambda: Point(0, TABS[state.tab].get_cursor_y(state)),
        ),
        width=HALF,
    )
    preview_window = Window(
        FormattedTextControl(lambda: render_preview_current(state)),
        wrap_lines=True,
        width=HALF,
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
                    list_window,
                    # 行末の CJK 文字が区切り線の桁へはみ出すのを空白で受ける
                    Window(width=1, char=" "),
                    Window(width=1, char="│"),
                    preview_window,
                ]
            ),
            Window(
                FormattedTextControl(lambda: render_status(state, conditions)), height=1
            ),
        ]
    )

    # Frame を VSplit で挟んで左右に幅1の空白パディングを置く。
    # Float の真下の行が CJK 文字 (display width=2) で終わると、その2セル目と
    # Frame の左ボーダーが同じ列に重なり、prompt_toolkit のレンダラが wide
    # char の幅ぶんカーソルを進めて Frame ボーダーのセルをスキップしてしまう
    # (= 縁が表示されない)。1セルの空白を挟むとスキップ先がボーダーではなく
    # 空白セルに変わるので、ボーダーは常に描画される。
    help_dialog = Float(
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
            filter=conditions.help_dialog,
        ),
    )

    filter_dialog = build_filter_dialog(state, conditions.issue_filter_dialog)
    find_dialog = build_find_dialog(state, conditions.issue_find_dialog)

    time_entry_filter_dialog = build_time_entry_filter_dialog(
        state, conditions.time_entry_filter_dialog
    )

    project_dialog = build_project_dialog(state, conditions.project_dialog)

    issue_delete_dialog = build_delete_dialog(state, conditions.issue_delete_dialog)
    wiki_delete_dialog = build_wiki_delete_dialog(state, conditions.wiki_delete_dialog)
    wiki_version_dialog = build_wiki_version_dialog(
        state, conditions.wiki_version_dialog
    )
    wiki_diff_dialog = build_wiki_diff_dialog(state, conditions.wiki_diff_dialog)
    profile_dialog = build_profile_dialog(state, conditions.profile_dialog)

    error_dialog = Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        Window(
                            FormattedTextControl(
                                lambda: render_error_dialog(state), show_cursor=False
                            ),
                            wrap_lines=True,
                        ),
                        title=lambda: messages.tui_error_dialog_title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=conditions.error_dialog,
        ),
    )

    return Layout(
        FloatContainer(
            content=main_layout,
            floats=[
                help_dialog,
                filter_dialog,
                find_dialog,
                time_entry_filter_dialog,
                project_dialog,
                issue_delete_dialog,
                wiki_delete_dialog,
                wiki_version_dialog,
                wiki_diff_dialog,
                profile_dialog,
                error_dialog,
            ],
        )
    )
