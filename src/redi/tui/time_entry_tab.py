import webbrowser

import requests

from redi.api.time_entry import fetch_issue_subjects, format_time_entry_line
from redi.client import client
from redi.config import default_project_id, redmine_url
from redi.i18n import messages
from redi.tui.render import highlight_segments, render_meta_table
from redi.tui.state import Renderable, TuiPosition, TuiResult, TuiState
from redi.tui.tab import TabView, noop, noop_jump


def _fetch_time_entries(project_id: str | None) -> list[dict]:
    if project_id:
        path = f"/projects/{project_id}/time_entries.json"
    else:
        path = "/time_entries.json"
    response = client.get(path)
    response.raise_for_status()
    return response.json()["time_entries"]


def _load_time_entries(state: TuiState) -> None:
    if state.time_entry_tab.loaded:
        return
    state.time_entry_tab.loaded = True
    try:
        entries = _fetch_time_entries(default_project_id)
    except requests.exceptions.RequestException as e:
        state.time_entry_tab.error = messages.tui_time_entry_load_failed.format(error=e)
        return
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
    state.time_entry_tab.entries = entries
    state.time_entry_tab.issue_subjects = subjects
    state.time_entry_tab.cursor = 0


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


def _status_hint(state: TuiState) -> str:
    return messages.tui_status_hint_time_entries


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
            position=TuiPosition(cursor=state.time_entry_tab.cursor),
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
            position=TuiPosition(cursor=state.time_entry_tab.cursor),
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
    if cursor >= len(entries):
        state.time_entry_tab.cursor = max(0, len(entries) - 1)


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
    ("  Tab / Shift+Tab", messages.tui_help_switch_tab),
    (messages.tui_help_section_search, ""),
    ("  /", messages.tui_help_start_search),
    ("  n / N", messages.tui_help_next_prev_match),
    (messages.tui_help_section_actions, ""),
    ("  c", messages.tui_help_time_entry_create),
    ("  u", messages.tui_help_time_entry_update),
    ("  D", messages.tui_help_time_entry_delete),
    ("  v", messages.tui_help_time_entry_open_web),
    (messages.tui_help_section_other, ""),
    ("  ?", messages.tui_help_show_or_close),
    ("  q / Esc / Ctrl+C", messages.tui_help_quit),
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
    on_page_forward=noop,
    on_page_backward=noop,
    on_open_web=_on_open_web,
    on_open_web_by_id=noop_jump,
    on_activate=_load_time_entries,
    on_action_key=_on_action_key,
    on_search=_on_search,
    get_cursor_y=lambda state: state.time_entry_tab.cursor,
    help_lines=_HELP_LINES,
)
