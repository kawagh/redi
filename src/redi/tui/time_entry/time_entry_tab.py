import webbrowser

import requests

from redi.api.time_entry import (
    fetch_issue_subjects,
    fetch_time_entries_page,
    format_time_entry_line,
)
from redi.client import client
from redi.config import redmine_url
from redi.i18n import messages
from redi.tui.render import highlight_segments, render_meta_table
from redi.tui.state import Renderable, TuiPosition, TuiResult, TuiState
from redi.tui.tab import TabView, noop, noop_jump


def _fetch_page_with_subjects(state: TuiState, offset: int) -> dict:
    """`offset` から始まる 1 ページ分の time_entries と issue subjects をまとめて返す。"""
    page = fetch_time_entries_page(
        project_id=state.effective_project_id(),
        user_id=state.time_entry_tab.filter.user_id,
        limit=state.page_size,
        offset=offset,
    )
    entries = page["time_entries"]
    issue_ids = sorted(
        {
            te["issue"]["id"]
            for te in entries
            if te.get("issue") and te["issue"].get("id")
        }
    )
    try:
        subjects = fetch_issue_subjects(issue_ids)
    except requests.exceptions.RequestException:
        subjects = {}
    return {
        "time_entries": entries,
        "total_count": page.get("total_count", len(entries)),
        "issue_subjects": subjects,
    }


def _apply_page(state: TuiState, page: dict, offset: int) -> None:
    state.time_entry_tab.offset = offset
    state.time_entry_tab.entries = page["time_entries"]
    state.time_entry_tab.total_count = page["total_count"]
    state.time_entry_tab.issue_subjects = page["issue_subjects"]
    state.time_entry_tab.cursor = 0


def _load_time_entries(state: TuiState) -> None:
    if state.time_entry_tab.loaded:
        return
    state.time_entry_tab.loaded = True
    try:
        page = _fetch_page_with_subjects(state, state.time_entry_tab.offset)
    except requests.exceptions.RequestException as e:
        state.time_entry_tab.error = messages.tui_time_entry_load_failed.format(error=e)
        return
    _apply_page(state, page, state.time_entry_tab.offset)


def _render_list(state: TuiState) -> Renderable:
    if state.time_entry_tab.error:
        return [("", state.time_entry_tab.error)]
    entries = state.time_entry_tab.entries
    if not entries:
        if state.time_entry_tab.loaded:
            return [("", messages.tui_time_entry_no_entries)]
        return [("", messages.tui_time_entry_loading)]
    result: Renderable = []
    query = state.search_query
    subjects = state.time_entry_tab.issue_subjects
    for i, te in enumerate(entries):
        prefix = "> " if i == state.time_entry_tab.cursor else "  "
        line = format_time_entry_line(te, issue_subjects=subjects)
        result.extend(highlight_segments(f"{prefix}{line}", query))
        result.append(("", "\n"))
    return result


def _render_preview(state: TuiState) -> Renderable:
    if state.time_entry_tab.error:
        return [("", state.time_entry_tab.error)]
    entries = state.time_entry_tab.entries
    if not entries:
        return [("", "")]
    te = entries[state.time_entry_tab.cursor]
    project = te.get("project") or {}
    user = te.get("user") or {}
    issue = te.get("issue") or {}
    issue_id = issue.get("id")
    subject = state.time_entry_tab.issue_subjects.get(issue_id) if issue_id else None
    title = f"#{te['id']} {te['hours']}h ({te['spent_on']})"
    if issue_id:
        ticket_cell = f"#{issue_id} {subject}" if subject else f"#{issue_id}"
    else:
        ticket_cell = ""
    meta = [
        (
            messages.tui_meta_project,
            f"{project.get('name', '')} (id={project.get('id', '')})",
        ),
        (
            messages.tui_meta_user,
            f"{user.get('name', '')} (id={user.get('id', '')})",
        ),
        (messages.tui_meta_activity, (te.get("activity") or {}).get("name", "")),
        (messages.tui_meta_issue, ticket_cell),
        (messages.tui_meta_created, te.get("created_on") or ""),
        (messages.tui_meta_updated, te.get("updated_on") or ""),
    ]
    lines = [title, ""]
    lines.extend(render_meta_table(meta))
    comments = te.get("comments")
    if comments:
        lines.append("")
        lines.append("----")
        lines.extend(comments.splitlines())
    return [("", "\n".join(lines))]


def _page_label(state: TuiState) -> str:
    total = state.time_entry_tab.total_count
    page_size = state.page_size or 1
    current = state.time_entry_tab.offset // page_size + 1
    total_pages = max(1, (total + page_size - 1) // page_size)
    count = len(state.time_entry_tab.entries)
    if count == 0:
        return f"Page {current}/{total_pages} (0 / {total})"
    start = state.time_entry_tab.offset + 1
    end = state.time_entry_tab.offset + count
    return f"Page {current}/{total_pages} ({start}-{end} / {total})"


def _status_hint(state: TuiState) -> str:
    hint = messages.tui_status_hint_time_entries.format(page_label=_page_label(state))
    if state.time_entry_tab.filter.is_active():
        hint = f" [{state.time_entry_tab.filter.short_label()}]" + hint
    return hint


def reload_with_filter(state: TuiState) -> None:
    """フィルタ条件で先頭ページから取得し直す。filter modal の適用で呼ぶ。"""
    state.time_entry_tab.error = None
    try:
        page = _fetch_page_with_subjects(state, 0)
    except requests.exceptions.RequestException as e:
        state.time_entry_tab.error = messages.tui_time_entry_load_failed.format(error=e)
        state.time_entry_tab.entries = []
        state.time_entry_tab.total_count = 0
        state.time_entry_tab.issue_subjects = {}
        state.time_entry_tab.offset = 0
        state.time_entry_tab.cursor = 0
        return
    _apply_page(state, page, 0)


def _on_action_key(state: TuiState, key: str) -> TuiResult | None:
    if key == "c":
        entries = state.time_entry_tab.entries
        issue_id: str | None = None
        if entries:
            te = entries[state.time_entry_tab.cursor]
            cursor_issue_id = (te.get("issue") or {}).get("id")
            if cursor_issue_id is not None:
                issue_id = str(cursor_issue_id)
        return TuiResult(
            action="create",
            tab="time_entries",
            issue_id=issue_id,
            position=TuiPosition(
                offset=state.time_entry_tab.offset,
                cursor=state.time_entry_tab.cursor,
            ),
        )
    if key == "u":
        entries = state.time_entry_tab.entries
        if not entries:
            return None
        te = entries[state.time_entry_tab.cursor]
        return TuiResult(
            action="update",
            tab="time_entries",
            time_entry_id=str(te["id"]),
            position=TuiPosition(
                offset=state.time_entry_tab.offset,
                cursor=state.time_entry_tab.cursor,
            ),
        )
    return None


def _on_up(state: TuiState) -> None:
    state.time_entry_tab.cursor = max(0, state.time_entry_tab.cursor - 1)


def _on_down(state: TuiState) -> None:
    if state.time_entry_tab.entries:
        state.time_entry_tab.cursor = min(
            len(state.time_entry_tab.entries) - 1,
            state.time_entry_tab.cursor + 1,
        )


def _on_goto_top(state: TuiState) -> None:
    if state.time_entry_tab.entries:
        state.time_entry_tab.cursor = 0


def _on_goto_bottom(state: TuiState) -> None:
    if state.time_entry_tab.entries:
        state.time_entry_tab.cursor = len(state.time_entry_tab.entries) - 1


def _on_search(state: TuiState, query: str, forward: bool = True) -> None:
    if not query:
        return
    entries = state.time_entry_tab.entries
    if not entries:
        return
    subjects = state.time_entry_tab.issue_subjects
    targets = [
        format_time_entry_line(te, issue_subjects=subjects).lower() for te in entries
    ]
    query_lower = query.lower()
    n = len(entries)
    step = 1 if forward else -1
    start = (state.time_entry_tab.cursor + step) % n
    for i in range(n):
        idx = (start + step * i) % n
        if query_lower in targets[idx]:
            state.time_entry_tab.cursor = idx
            return


def request_delete(state: TuiState) -> str | None:
    """カーソル行の削除確認プロンプトを返す。対象がなければ None。"""
    entries = state.time_entry_tab.entries
    if not entries:
        return None
    te = entries[state.time_entry_tab.cursor]
    summary = format_time_entry_line(
        te, issue_subjects=state.time_entry_tab.issue_subjects
    )
    return messages.tui_time_entry_delete_prompt.format(summary=summary)


def confirm_delete(state: TuiState) -> None:
    """カーソル行の time_entry を削除する。失敗時は error を設定する。"""
    entries = state.time_entry_tab.entries
    if not entries:
        return
    cursor = state.time_entry_tab.cursor
    te = entries[cursor]
    try:
        response = client.delete(f"/time_entries/{te['id']}.json")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        state.flash_message = messages.tui_time_entry_delete_failed.format(error=e)
        return
    entries.pop(cursor)
    state.time_entry_tab.total_count = max(0, state.time_entry_tab.total_count - 1)
    if cursor >= len(entries):
        state.time_entry_tab.cursor = max(0, len(entries) - 1)


def _on_reload(state: TuiState) -> None:
    """現在のページのまま time_entry 一覧を取り直す。

    同じ id の entry が残っていればその位置に cursor を復元し、無ければ
    元の cursor 位置を新一覧の範囲内にクランプする。
    """
    prev_id: int | None = None
    if state.time_entry_tab.entries:
        prev_id = state.time_entry_tab.entries[state.time_entry_tab.cursor].get("id")
    prev_cursor = state.time_entry_tab.cursor
    state.time_entry_tab.error = None
    try:
        page = _fetch_page_with_subjects(state, state.time_entry_tab.offset)
    except requests.exceptions.RequestException as e:
        state.time_entry_tab.error = messages.tui_time_entry_load_failed.format(error=e)
        return
    state.time_entry_tab.entries = page["time_entries"]
    state.time_entry_tab.total_count = page["total_count"]
    state.time_entry_tab.issue_subjects = page["issue_subjects"]
    if not state.time_entry_tab.entries:
        state.time_entry_tab.cursor = 0
        return
    if prev_id is not None:
        for i, te in enumerate(state.time_entry_tab.entries):
            if te.get("id") == prev_id:
                state.time_entry_tab.cursor = i
                return
    state.time_entry_tab.cursor = max(
        0, min(prev_cursor, len(state.time_entry_tab.entries) - 1)
    )


def _on_page_forward(state: TuiState) -> None:
    next_offset = state.time_entry_tab.offset + state.page_size
    try:
        page = _fetch_page_with_subjects(state, next_offset)
    except requests.exceptions.RequestException as e:
        state.time_entry_tab.error = messages.tui_time_entry_load_failed.format(error=e)
        return
    if page["time_entries"]:
        _apply_page(state, page, next_offset)


def _on_page_backward(state: TuiState) -> None:
    if state.time_entry_tab.offset <= 0:
        return
    prev_offset = max(0, state.time_entry_tab.offset - state.page_size)
    try:
        page = _fetch_page_with_subjects(state, prev_offset)
    except requests.exceptions.RequestException as e:
        state.time_entry_tab.error = messages.tui_time_entry_load_failed.format(error=e)
        return
    _apply_page(state, page, prev_offset)


def _on_open_web(state: TuiState) -> None:
    entries = state.time_entry_tab.entries
    if not entries:
        return
    te = entries[state.time_entry_tab.cursor]
    issue_id = (te.get("issue") or {}).get("id")
    if issue_id:
        webbrowser.open(f"{redmine_url}/issues/{issue_id}")
    else:
        webbrowser.open(f"{redmine_url}/time_entries")


_HELP_LINES: list[tuple[str, str]] = [
    (messages.tui_help_section_navigation, ""),
    ("  ↑/k/Ctrl+P", messages.tui_help_move_up),
    ("  ↓/j/Ctrl+N", messages.tui_help_move_down),
    ("  gg / G", messages.tui_help_goto_top_bottom),
    ("  ←/h / →/l", messages.tui_help_prev_next_page),
    ("  Tab / Shift+Tab", messages.tui_help_switch_tab),
    ("  Ctrl+E / Ctrl+Y", messages.tui_help_preview_scroll_line),
    ("  Ctrl+D / Ctrl+U", messages.tui_help_preview_scroll_half_page),
    (messages.tui_help_section_search, ""),
    ("  /", messages.tui_help_start_search),
    ("  n / N", messages.tui_help_next_prev_match),
    (messages.tui_help_section_filter, ""),
    ("  f", messages.tui_help_filter_user),
    ("  p", messages.tui_help_switch_project),
    (messages.tui_help_section_actions, ""),
    ("  c", messages.tui_help_time_entry_create),
    ("  u", messages.tui_help_time_entry_update),
    ("  D", messages.tui_help_time_entry_delete),
    ("  v", messages.tui_help_time_entry_open_web),
    ("  R", messages.tui_help_reload),
    (messages.tui_help_section_other, ""),
    ("  ?", messages.tui_help_show_or_close),
    ("  q / Ctrl+C", messages.tui_help_quit),
]


TIME_ENTRY_TAB = TabView(
    label=messages.tui_tab_label_time_entries,
    render_list=_render_list,
    render_preview=_render_preview,
    status_hint=_status_hint,
    on_up=_on_up,
    on_down=_on_down,
    on_goto_top=_on_goto_top,
    on_goto_bottom=_on_goto_bottom,
    on_jump_to_id=noop_jump,
    on_enter=noop,
    on_page_forward=_on_page_forward,
    on_page_backward=_on_page_backward,
    on_open_web=_on_open_web,
    on_open_web_by_id=noop_jump,
    on_activate=_load_time_entries,
    on_reload=_on_reload,
    on_action_key=_on_action_key,
    on_search=_on_search,
    get_cursor_y=lambda state: state.time_entry_tab.cursor,
    help_lines=_HELP_LINES,
)
