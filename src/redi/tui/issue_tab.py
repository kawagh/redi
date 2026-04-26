import webbrowser

from redi.api.issue import fetch_issue, fetch_issues_page
from redi.config import default_project_id, redmine_url
from redi.i18n import messages
from redi.tui.render import highlight_segments, render_meta_table
from redi.tui.state import Renderable, TuiAction, TuiPosition, TuiResult, TuiState
from redi.tui.tab import TabView, noop


def load_journals(issue: dict) -> None:
    fetched = fetch_issue(str(issue["id"]), include="journals")
    issue["journals"] = fetched.get("journals") or []


def _exit_result(
    state: TuiState, action: TuiAction, issue_id: str | None = None
) -> TuiResult:
    if issue_id is None and state.issue_tab.issues:
        issue_id = str(state.issue_tab.issues[state.issue_tab.cursor]["id"])
    return TuiResult(
        action=action,
        tab="issues",
        issue_id=issue_id,
        position=TuiPosition(
            offset=state.issue_tab.offset, cursor=state.issue_tab.cursor
        ),
    )


def _render_list(state: TuiState) -> Renderable:
    result: Renderable = []
    query = state.search_query
    for i, issue in enumerate(state.issue_tab.issues):
        prefix = "> " if i == state.issue_tab.cursor else "  "
        text = f"{prefix}#{issue['id']} {issue['subject']}"
        result.extend(highlight_segments(text, query))
        result.append(("", "\n"))
    return result


def _render_preview(state: TuiState) -> Renderable:
    if not state.issue_tab.issues:
        return []
    issue = state.issue_tab.issues[state.issue_tab.cursor]
    lines = [f"#{issue.get('id', '')} {issue.get('subject', '')}", ""]

    def named(field: str) -> str:
        value = issue.get(field)
        if isinstance(value, dict):
            return value.get("name", "")
        return ""

    meta = [
        (messages.tui_meta_status, named("status")),
        (messages.tui_meta_priority, named("priority")),
        (messages.tui_meta_tracker, named("tracker")),
        (messages.tui_meta_assignee, named("assigned_to")),
        (messages.tui_meta_author, named("author")),
        (messages.tui_meta_start_date, issue.get("start_date") or ""),
        (messages.tui_meta_due_date, issue.get("due_date") or ""),
        (
            messages.tui_meta_progress,
            f"{issue['done_ratio']}%" if issue.get("done_ratio") is not None else "",
        ),
        (
            messages.tui_meta_estimated_hours,
            f"{issue['estimated_hours']} h"
            if issue.get("estimated_hours") is not None
            else "",
        ),
        (
            messages.tui_meta_spent_hours,
            f"{issue['spent_hours']} h" if issue.get("spent_hours") is not None else "",
        ),
        (messages.tui_meta_created, issue.get("created_on") or ""),
        (messages.tui_meta_updated, issue.get("updated_on") or ""),
    ]
    lines.extend(render_meta_table(meta))

    description = issue.get("description") or ""
    if description:
        lines.append("")
        lines.append("----")
        lines.extend(description.splitlines())

    journals = issue.get("journals") or []
    notes = [j for j in journals if (j.get("notes") or "").strip()]
    if notes:
        lines.append("")
        lines.append("----")
        lines.append(messages.tui_preview_comments_header)
        for j in notes:
            author = (j.get("user") or {}).get("name", "")
            created = j.get("created_on", "")
            lines.append(f"[{created}] {author}")
            for nl in (j.get("notes") or "").splitlines():
                lines.append(f"  {nl}")

    return [("", "\n".join(lines))]


def _status_hint(state: TuiState) -> str:
    hint = messages.tui_status_hint_issues.format(page_label=_page_label(state))
    if state.issue_tab.filter.is_active():
        hint = f" [{state.issue_tab.filter.short_label()}]" + hint
    return hint


def _page_label(state: TuiState) -> str:
    total = state.issue_tab.total_count
    page_size = state.page_size or 1
    current = state.issue_tab.offset // page_size + 1
    total_pages = max(1, (total + page_size - 1) // page_size)
    count = len(state.issue_tab.issues)
    if count == 0:
        return f"Page {current}/{total_pages} (0 / {total})"
    start = state.issue_tab.offset + 1
    end = state.issue_tab.offset + count
    return f"Page {current}/{total_pages} ({start}-{end} / {total})"


def _on_up(state: TuiState) -> None:
    state.issue_tab.cursor = max(0, state.issue_tab.cursor - 1)


def _on_down(state: TuiState) -> None:
    state.issue_tab.cursor = min(
        len(state.issue_tab.issues) - 1, state.issue_tab.cursor + 1
    )


def _on_goto_top(state: TuiState) -> None:
    if state.issue_tab.issues:
        state.issue_tab.cursor = 0


def _on_goto_bottom(state: TuiState) -> None:
    if state.issue_tab.issues:
        state.issue_tab.cursor = len(state.issue_tab.issues) - 1


def _on_jump_to_id(state: TuiState, target_id: int) -> None:
    for i, issue in enumerate(state.issue_tab.issues):
        if issue.get("id") == target_id:
            state.issue_tab.cursor = i
            return


def _on_enter(state: TuiState) -> None:
    if not state.issue_tab.issues:
        return
    issue = state.issue_tab.issues[state.issue_tab.cursor]
    if issue.get("id") is None:
        return
    load_journals(issue)


def fetch_issues_with_filter(state: TuiState, offset: int) -> dict:
    f = state.issue_tab.filter
    return fetch_issues_page(
        project_id=default_project_id,
        status_id=f.status_id,
        assigned_to=f.assigned_to_id,
        limit=state.page_size,
        offset=offset,
    )


def _apply_page(state: TuiState, page: dict, offset: int) -> None:
    state.issue_tab.offset = offset
    state.issue_tab.issues = page["issues"]
    state.issue_tab.total_count = page.get("total_count", len(page["issues"]))
    state.issue_tab.cursor = 0


def reload_with_filter(state: TuiState) -> None:
    """フィルタ条件で先頭ページから再取得する。filter modal からの適用で呼ぶ。"""
    _apply_page(state, fetch_issues_with_filter(state, 0), 0)


def _on_page_forward(state: TuiState) -> None:
    next_offset = state.issue_tab.offset + state.page_size
    page = fetch_issues_with_filter(state, next_offset)
    if page["issues"]:
        _apply_page(state, page, next_offset)


def _on_page_backward(state: TuiState) -> None:
    if state.issue_tab.offset <= 0:
        return
    prev_offset = max(0, state.issue_tab.offset - state.page_size)
    _apply_page(state, fetch_issues_with_filter(state, prev_offset), prev_offset)


def _on_open_web(state: TuiState) -> None:
    if not state.issue_tab.issues:
        return
    issue_id = state.issue_tab.issues[state.issue_tab.cursor]["id"]
    webbrowser.open(f"{redmine_url}/issues/{issue_id}")


def _on_open_web_by_id(state: TuiState, target_id: int) -> None:
    webbrowser.open(f"{redmine_url}/issues/{target_id}")


def _on_search(state: TuiState, query: str, forward: bool = True) -> None:
    if not query:
        return
    issues = state.issue_tab.issues
    if not issues:
        return
    targets = [
        f"#{issue.get('id', '')} {issue.get('subject', '')}".lower() for issue in issues
    ]
    query_lower = query.lower()
    n = len(issues)
    step = 1 if forward else -1
    start = (state.issue_tab.cursor + step) % n
    for i in range(n):
        idx = (start + step * i) % n
        if query_lower in targets[idx]:
            state.issue_tab.cursor = idx
            return


def _on_action_key(state: TuiState, key: str) -> TuiResult | None:
    if key == "u":
        return _exit_result(state, "update")
    if key == "c":
        return _exit_result(state, "create", issue_id="")
    if key == "n":
        return _exit_result(state, "comment")
    if key == "t":
        if not state.issue_tab.issues:
            return None
        return _exit_result(state, "create_time_entry")
    return None


_HELP_LINES: list[tuple[str, str]] = [
    (messages.tui_help_section_navigation, ""),
    ("  ↑/k/Ctrl+P", messages.tui_help_move_up),
    ("  ↓/j/Ctrl+N", messages.tui_help_move_down),
    ("  gg / G", messages.tui_help_goto_top_bottom),
    ("  <N>G", messages.tui_help_jump_to_issue_n),
    ("  ←/h / →/l", messages.tui_help_prev_next_page),
    ("  Tab / Shift+Tab", messages.tui_help_switch_tab),
    (messages.tui_help_section_search, ""),
    ("  /", messages.tui_help_start_search),
    ("  n / N", messages.tui_help_next_prev_match),
    (messages.tui_help_section_filter, ""),
    ("  f", messages.tui_help_filter_status_assignee),
    (messages.tui_help_section_actions, ""),
    ("  Enter", messages.tui_help_issue_load_comments),
    ("  c / u", messages.tui_help_issue_create_or_update),
    ("  n", messages.tui_help_issue_add_comment),
    ("  t", messages.tui_help_issue_create_time_entry),
    ("  v / <N>V", messages.tui_help_issue_open_web_or_n),
    (messages.tui_help_section_other, ""),
    ("  ?", messages.tui_help_show_or_close),
    ("  q / Esc / Ctrl+C", messages.tui_help_quit),
]


ISSUE_TAB = TabView(
    label=messages.tui_tab_label_issues,
    render_list=_render_list,
    render_preview=_render_preview,
    status_hint=_status_hint,
    on_up=_on_up,
    on_down=_on_down,
    on_goto_top=_on_goto_top,
    on_goto_bottom=_on_goto_bottom,
    on_jump_to_id=_on_jump_to_id,
    on_enter=_on_enter,
    on_page_forward=_on_page_forward,
    on_page_backward=_on_page_backward,
    on_open_web=_on_open_web,
    on_open_web_by_id=_on_open_web_by_id,
    on_activate=noop,
    on_action_key=_on_action_key,
    on_search=_on_search,
    get_cursor_y=lambda state: state.issue_tab.cursor,
    help_lines=_HELP_LINES,
)
