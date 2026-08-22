import shutil
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings

from redi.service import me_service
from redi.tui.app_layout import build_layout
from redi.tui.conditions import build_conditions
from redi.tui.issue.issue_tab import fetch_issues_with_filter, load_journals
from redi.tui.keybindings import (
    modal_keybindings,
    normal_keybindings,
    submode_keybindings,
)
from redi.tui.resize import attach_resize_watcher
from redi.tui.screen_log import attach_screen_log
from redi.tui.state import (
    TuiPosition,
    TuiResult,
    TuiState,
    compute_page_size,
)
from redi.tui.tabs import TABS


def _restore_session(state: TuiState) -> None:
    """前回の `TuiResult` からタブ・位置・journal を復元し、初回のデータを取る。

    TUI は編集のたびに一度終了して外部エディタへ抜けるため、戻ってきたときに
    直前の見え方へ復帰させる必要がある。
    """
    last = state.last_result
    if last:
        state.tab = last.tab
    position = last.position if last else TuiPosition()
    state.page_size = compute_page_size(shutil.get_terminal_size().lines)
    initial_offset = position.offset if state.tab == "issues" else 0
    initial_page = fetch_issues_with_filter(state, initial_offset)
    state.issue_tab.offset = initial_offset
    state.issue_tab.issues = initial_page["issues"]
    state.issue_tab.total_count = initial_page.get(
        "total_count", len(state.issue_tab.issues)
    )
    if state.issue_tab.issues:
        state.issue_tab.cursor = max(
            0, min(position.cursor, len(state.issue_tab.issues) - 1)
        )
    # journalの更新
    if (
        last
        and last.action in ("comment", "edit_comment", "delete_comment")
        and last.issue_id
    ):
        target_id = int(last.issue_id)
        target = next(
            (i for i in state.issue_tab.issues if i.get("id") == target_id), None
        )
        if target is not None:
            load_journals(target)
    if state.tab == "wiki":
        TABS["wiki"].on_activate(state)
        if last and last.tab == "wiki" and last.wiki_title:
            titles = [p.get("title") for p in state.wiki_tab.pages]
            if last.wiki_title in titles:
                state.wiki_tab.cursor = titles.index(last.wiki_title)
    if state.tab == "time_entries":
        if last and last.tab == "time_entries":
            state.time_entry_tab.offset = last.position.offset
        TABS["time_entries"].on_activate(state)
        if last and last.tab == "time_entries":
            max_cursor = max(0, len(state.time_entry_tab.entries) - 1)
            state.time_entry_tab.cursor = min(last.position.cursor, max_cursor)


def run_issue_tui(
    state: TuiState | None = None,
    debug_log_path: Path | None = None,
) -> TuiResult | None:
    if state is None:
        state = TuiState()
    if state.me_id is None:
        state.me_id = me_service.read_my_user_id()
    _restore_session(state)

    conditions = build_conditions(state)
    kb = KeyBindings()
    normal_keybindings.register(kb, state, conditions)
    modal_keybindings.register(kb, state, conditions)
    submode_keybindings.register(kb, state, conditions)

    app = Application(
        layout=build_layout(state, conditions),
        key_bindings=kb,
        full_screen=True,
    )

    attach_resize_watcher(app, state, conditions)

    if debug_log_path is not None:
        attach_screen_log(app, debug_log_path)

    return app.run()
