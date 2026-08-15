"""time_entries タブの f で開くフィルタ modal のレイアウトと描画。"""

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
from redi.tui.choices import build_user_choices
from redi.tui.state import Renderable, TimeEntryFilterModalState, TuiState


def render_filter_column(state: TuiState) -> Renderable:
    """ユーザー選択肢の列を描画する。"""
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
    return parts


def filter_column_cursor_y(modal: TimeEntryFilterModalState) -> int:
    """`render_filter_column` の描画結果におけるカーソル行 (0 始まり)。

    Window にカーソル位置を伝えて選択中の行が常に画面内へ来るようスクロール
    させるために使う。0 行目はセクションヘッダなので選択肢は 1 行目から並ぶ。
    """
    return 1 + modal.user_cursor


def build_filter_float(state: TuiState, show: FilterOrBool) -> Float:
    """time_entries タブのフィルタ modal の Float を組み立てる。

    プロジェクトのユーザーが多いと選択肢が端末高を超えるため、列に
    `get_cursor_position` を渡してカーソル行が画面内に収まるようスクロール
    させる。ヒントは列とは別の Window に置き、スクロールしても常に見せる。

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
                                        lambda: render_filter_column(state),
                                        show_cursor=False,
                                        get_cursor_position=lambda: Point(
                                            0,
                                            filter_column_cursor_y(
                                                state.time_entry_tab.filter_modal
                                            ),
                                        ),
                                    ),
                                    wrap_lines=False,
                                    scroll_offsets=ScrollOffsets(top=1, bottom=1),
                                ),
                                # ヒントは列のスクロール対象から外して常に見せる
                                Window(
                                    FormattedTextControl(
                                        messages.tui_filter_hint_single,
                                        show_cursor=False,
                                    ),
                                    height=1,
                                ),
                            ]
                        ),
                        title=messages.tui_filter_title_time_entries,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=show,
        ),
    )


def open_filter_modal(state: TuiState) -> None:
    """フィルタ modal を開く。選択肢を取り直し、現在の絞り込みにカーソルを合わせる。"""
    modal = state.time_entry_tab.filter_modal
    modal.user_choices = build_user_choices(state.effective_project_id(), state.me_id)
    modal.user_cursor = 0
    for idx, (api_val, _label) in enumerate(modal.user_choices):
        if api_val == state.time_entry_tab.filter.user_id:
            modal.user_cursor = idx
            break
    modal.show = True
