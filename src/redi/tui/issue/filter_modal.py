"""issues タブの f で開くフィルタ modal のレイアウトと描画。

ステータスと担当者を 2 列に並べ、列ごとに独立してスクロールさせる。縦に連結
すると modal の高さが選択肢数の合計になり、選択肢が多い環境で下部が端末外へ
溢れてしまうため。
"""

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
from redi.tui.choices import build_assignee_choices, build_status_choices
from redi.tui.state import (
    FilterField,
    FilterModalState,
    Renderable,
    TuiState,
)


def _render_filter_section(
    modal: FilterModalState,
    section: FilterField,
    title: str,
    choices: list[tuple[str | None, str]],
    cursor: int,
    active_id: str | None,
) -> Renderable:
    focused = modal.focus == section
    header_style = "bold fg:ansicyan" if focused else "bold"
    parts: Renderable = [(header_style, f"[{title}]\n")]
    for i, (api_val, label) in enumerate(choices):
        is_cursor = focused and i == cursor
        is_active = api_val == active_id
        cursor_mark = ">" if is_cursor else " "
        active_mark = "*" if is_active else " "
        line_style = "reverse" if is_cursor else ("bold" if is_active else "")
        parts.append((line_style, f" {cursor_mark} {active_mark} {label}\n"))
    return parts


def render_filter_column(state: TuiState, section: FilterField) -> Renderable:
    """フィルタ modal の 1 列 (status か assignee) を描画する。

    2 列を縦に連結せず列ごとに描くことで、modal の高さが選択肢数の合計ではなく
    max(status, assignee) で済み、選択肢が多くても縦に溢れにくくなる。
    """
    f = state.issue_tab.filter
    modal = state.issue_tab.filter_modal
    if section == "status":
        return _render_filter_section(
            modal,
            "status",
            messages.tui_filter_status,
            modal.status_choices,
            modal.status_cursor,
            f.status_id,
        )
    return _render_filter_section(
        modal,
        "assignee",
        messages.tui_filter_assignee,
        modal.assignee_choices,
        modal.assignee_cursor,
        f.assigned_to_id,
    )


def filter_column_cursor_y(modal: FilterModalState, section: FilterField) -> int:
    """`render_filter_column` の描画結果におけるカーソル行 (0 始まり)。

    Window にカーソル位置を伝えて選択中の行が常に画面内へ来るようスクロール
    させるために使う。0 行目はセクションヘッダなので選択肢は 1 行目から並ぶ。
    """
    cursor = modal.status_cursor if section == "status" else modal.assignee_cursor
    return 1 + cursor


def _filter_column_window(state: TuiState, section: FilterField) -> Window:
    """フィルタ modal の 1 列を載せる Window。

    選択肢が端末高を超えると Float が高さを端末内へ切り詰め、Window にはその
    切り詰め後の高さが渡る。`get_cursor_position` を与えておくと Window が
    カーソル行を画面内に収めるようスクロールしてくれるので、選択肢が多くても
    選択中の行を見失わない (渡さないと vertical_scroll が 0 のまま先頭が出続け、
    下の方の選択肢が見えなくなる)。
    """
    return Window(
        FormattedTextControl(
            lambda: render_filter_column(state, section),
            show_cursor=False,
            get_cursor_position=lambda: Point(
                0, filter_column_cursor_y(state.issue_tab.filter_modal, section)
            ),
        ),
        wrap_lines=False,
        scroll_offsets=ScrollOffsets(top=1, bottom=1),
    )


def build_filter_float(state: TuiState, show: FilterOrBool) -> Float:
    """フィルタ modal の Float を組み立てる。

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
                                VSplit(
                                    [
                                        _filter_column_window(state, "status"),
                                        Window(width=1, char=" "),
                                        Window(width=1, char="│"),
                                        Window(width=1, char=" "),
                                        _filter_column_window(state, "assignee"),
                                    ]
                                ),
                                # ヒントは列のスクロール対象から外して常に見せる
                                Window(
                                    FormattedTextControl(
                                        messages.tui_filter_hint, show_cursor=False
                                    ),
                                    height=1,
                                ),
                            ]
                        ),
                        title=messages.tui_filter_title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=show,
        ),
    )


def open_filter_modal(state: TuiState) -> None:
    """フィルタ modal を開く。選択肢を取り直し、現在の絞り込みにカーソルを合わせる。"""
    modal = state.issue_tab.filter_modal
    modal.status_choices = build_status_choices()
    modal.assignee_choices = build_assignee_choices(
        state.effective_project_id(), state.me_id
    )
    modal.status_cursor = 0
    for idx, (api_val, _label) in enumerate(modal.status_choices):
        if api_val == state.issue_tab.filter.status_id:
            modal.status_cursor = idx
            break
    modal.assignee_cursor = 0
    for idx, (api_val, _label) in enumerate(modal.assignee_choices):
        if api_val == state.issue_tab.filter.assigned_to_id:
            modal.assignee_cursor = idx
            break
    modal.focus = "status"
    modal.show = True
