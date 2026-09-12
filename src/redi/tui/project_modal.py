"""p で開くプロジェクト切替 modal の描画と、開く/切り替える操作。"""

import requests
from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.layout.containers import Float

from redi.i18n import messages
from redi.service.project_service import list_projects, sort_projects_by_id_desc
from redi.tui.choice_modal import build_choice_float
from redi.tui.issue.issue_tab import reload_with_filter
from redi.tui.state import (
    TimeEntryFilter,
    TimeEntryTabState,
    TuiState,
    WikiTabState,
)
from redi.tui.tabs import TABS


def build_project_float(state: TuiState, show: FilterOrBool) -> Float:
    return build_choice_float(
        lambda: state.project_modal,
        messages.tui_project_modal_title,
        messages.tui_project_modal_hint,
        show,
    )


def open_project_modal(state: TuiState) -> None:
    """プロジェクト切替モーダルを開く。一覧取得に失敗したら error modal に流す。"""
    modal = state.project_modal
    try:
        projects = sort_projects_by_id_desc(list_projects(all_pages=True))
    except requests.exceptions.RequestException as e:
        state.error_modal = messages.tui_project_load_failed.format(error=e)
        return
    modal.choices = [(str(p["id"]), p.get("name", "")) for p in projects]
    modal.cursor = 0
    # config には id のほか identifier も設定できるので両方で現在プロジェクトを
    # 探し、id へ解決して保持する (`*` 表示とカーソル初期位置に使う)。
    modal.active_value = None
    current = state.effective_project_id()
    if current is not None:
        for idx, p in enumerate(projects):
            if str(p["id"]) == str(current) or p.get("identifier") == current:
                modal.active_value = str(p["id"])
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
    # クエリはプロジェクト固有のものが混ざるので、切り替えたら必ず外す。
    issue_filter.clear_query()
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
