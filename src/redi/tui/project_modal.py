"""p で開くプロジェクト切替 modal の描画と、開く/切り替える操作。"""

import requests
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

from redi.api.project import fetch_projects, sort_projects_by_id_desc
from redi.i18n import messages
from redi.tui.issue.issue_tab import reload_with_filter
from redi.tui.state import (
    Renderable,
    TimeEntryFilter,
    TimeEntryTabState,
    TuiState,
    WikiTabState,
)
from redi.tui.tabs import TABS


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
                                        messages.tui_project_modal_hint,
                                        show_cursor=False,
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


def open_project_modal(state: TuiState) -> None:
    """プロジェクト切替モーダルを開く。一覧取得に失敗したら error modal に流す。"""
    modal = state.project_modal
    try:
        projects = sort_projects_by_id_desc(fetch_projects())
    except requests.exceptions.RequestException as e:
        state.error_modal = messages.tui_project_load_failed.format(error=e)
        return
    modal.choices = [(str(p["id"]), p.get("name", "")) for p in projects]
    modal.cursor = 0
    # config には id のほか identifier も設定できるので両方で現在プロジェクトを
    # 探し、id へ解決して保持する (`*` 表示とカーソル初期位置に使う)。
    modal.active_id = None
    current = state.effective_project_id()
    if current is not None:
        for idx, p in enumerate(projects):
            if str(p["id"]) == str(current) or p.get("identifier") == current:
                modal.active_id = str(p["id"])
                modal.cursor = idx
                break
    modal.show = True


def apply_project_switch(state: TuiState, project_id: str, label: str) -> None:
    """セッション内のプロジェクトを切り替え、全タブを新プロジェクトで取り直す。"""
    state.project_id = project_id
    state.project_label = label
    state.project_modal.show = False
    # 数値 id のフィルタは旧プロジェクトのユーザーを指すのでクリアする。
    # プロジェクト非依存の特殊値 (未設定/me/未割当) と status は保持する。
    issue_filter = state.issue_tab.filter
    if issue_filter.assigned_to_id not in (None, "me", "!*"):
        issue_filter.assigned_to_id = None
        issue_filter.assigned_to_label = messages.tui_filter_assignee_none
    te_filter = state.time_entry_tab.filter
    if te_filter.user_id not in (None, "me"):
        te_filter = TimeEntryFilter()
    # time_entry / wiki は state を作り直して遅延再取得に任せる。
    # wiki の texts はタイトルのみがキーなので、残すと別プロジェクトの同名
    # ページに旧本文が表示されてしまう。
    state.time_entry_tab = TimeEntryTabState(filter=te_filter)
    state.wiki_tab = WikiTabState()
    state.preview_scroll = 0
    # issues タブは on_activate が noop で遅延再取得できないため即時取り直す。
    reload_with_filter(state)
    if state.tab in ("time_entries", "wiki"):
        TABS[state.tab].on_activate(state)
    state.flash_message = messages.tui_flash_project_switched.format(name=label)
