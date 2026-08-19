"""issues タブの f で開くフィルタ modal のレイアウトと描画。

ステータス・担当者・トラッカーを 3 列に並べ、列ごとに独立してスクロールさせる。
縦に連結すると modal の高さが選択肢数の合計になり、選択肢が多い環境で下部が
端末外へ溢れてしまうため。
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
from redi.tui.choices import (
    build_assignee_choices,
    build_status_choices,
    build_tracker_choices,
)
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


# 列の並び順。focus の左右移動もこの順に巡回する。
FILTER_SECTIONS: tuple[FilterField, ...] = ("status", "assignee", "tracker")


def shift_focus(current: FilterField, step: int) -> FilterField:
    """focus を step だけ動かす。端では反対側へ巡回する。"""
    idx = FILTER_SECTIONS.index(current)
    return FILTER_SECTIONS[(idx + step) % len(FILTER_SECTIONS)]


def section_choices(
    modal: FilterModalState, section: FilterField
) -> list[tuple[str | None, str]]:
    """セクションに対応する選択肢リストを返す。"""
    match section:
        case "status":
            return modal.status_choices
        case "assignee":
            return modal.assignee_choices
        case "tracker":
            return modal.tracker_choices


def section_cursor(modal: FilterModalState, section: FilterField) -> int:
    """セクションに対応するカーソル位置を返す。"""
    match section:
        case "status":
            return modal.status_cursor
        case "assignee":
            return modal.assignee_cursor
        case "tracker":
            return modal.tracker_cursor


def set_section_cursor(
    modal: FilterModalState, section: FilterField, cursor: int
) -> None:
    """セクションに対応するカーソル位置を更新する。"""
    match section:
        case "status":
            modal.status_cursor = cursor
        case "assignee":
            modal.assignee_cursor = cursor
        case "tracker":
            modal.tracker_cursor = cursor


def render_filter_column(state: TuiState, section: FilterField) -> Renderable:
    """フィルタ modal の 1 列 (status / assignee / tracker) を描画する。

    3 列を縦に連結せず列ごとに描くことで、modal の高さが選択肢数の合計ではなく
    max(status, assignee, tracker) で済み、選択肢が多くても縦に溢れにくくなる。
    """
    f = state.issue_tab.filter
    modal = state.issue_tab.filter_modal
    if section == "status":
        title, active_id = messages.tui_filter_status, f.status_id
    elif section == "assignee":
        title, active_id = messages.tui_filter_assignee, f.assigned_to_id
    else:
        title, active_id = messages.tui_filter_tracker, f.tracker_id
    return _render_filter_section(
        modal,
        section,
        title,
        section_choices(modal, section),
        section_cursor(modal, section),
        active_id,
    )


def filter_column_cursor_y(modal: FilterModalState, section: FilterField) -> int:
    """`render_filter_column` の描画結果におけるカーソル行 (0 始まり)。

    Window にカーソル位置を伝えて選択中の行が常に画面内へ来るようスクロール
    させるために使う。0 行目はセクションヘッダなので選択肢は 1 行目から並ぶ。
    """
    return 1 + section_cursor(modal, section)


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


def _column_separator() -> list[Window]:
    """列と列の間に置く区切り (空白 + 罫線 + 空白)。"""
    return [
        Window(width=1, char=" "),
        Window(width=1, char="│"),
        Window(width=1, char=" "),
    ]


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
                                        *_column_separator(),
                                        _filter_column_window(state, "assignee"),
                                        *_column_separator(),
                                        _filter_column_window(state, "tracker"),
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
    f = state.issue_tab.filter
    modal.status_choices = build_status_choices()
    modal.assignee_choices = build_assignee_choices(
        state.effective_project_id(), state.me_id
    )
    modal.tracker_choices = build_tracker_choices()
    actives: list[tuple[FilterField, str | None]] = [
        ("status", f.status_id),
        ("assignee", f.assigned_to_id),
        ("tracker", f.tracker_id),
    ]
    for section, active_id in actives:
        cursor = 0
        for idx, (api_val, _label) in enumerate(section_choices(modal, section)):
            if api_val == active_id:
                cursor = idx
                break
        set_section_cursor(modal, section, cursor)
    modal.focus = "status"
    modal.show = True
