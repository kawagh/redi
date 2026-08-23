import webbrowser

from redi import config
from redi.api.issue import (
    Issue,
    IssuesPageResponse,
    Journal,
    fetch_issues_page,
)
from redi.i18n import messages
from redi.service import issue_service
from redi.text_format import highlight_segments, issue_meta_rows, render_meta_table
from redi.tui.state import (
    CommentSelectState,
    Renderable,
    TuiAction,
    TuiPosition,
    TuiResult,
    TuiState,
)
from redi.tui.tab import TabView, noop


def load_journals(issue: Issue) -> None:
    fetched = issue_service.read_issue(str(issue["id"]), include="journals")
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
    if not state.issue_tab.issues:
        return [("", messages.issue_not_found_simple)]
    result: Renderable = []
    query = state.search_query
    for i, issue in enumerate(state.issue_tab.issues):
        prefix = "> " if i == state.issue_tab.cursor else "  "
        text = f"{prefix}#{issue['id']} {issue['subject']}"
        result.extend(highlight_segments(text, query))
        result.append(("", "\n"))
    return result


def _notes_journals(issue: Issue) -> list[tuple[int, Journal]]:
    journals = issue.get("journals") or []
    return [
        (i, journal)
        for i, journal in enumerate(journals)
        if (journal.get("notes") or "").strip()
    ]


def _render_preview(state: TuiState) -> Renderable:
    if not state.issue_tab.issues:
        return []
    issue = state.issue_tab.issues[state.issue_tab.cursor]
    parts: Renderable = []
    head_lines = [f"#{issue.get('id', '')} {issue.get('subject', '')}", ""]
    head_lines.extend(render_meta_table(issue_meta_rows(issue)))

    description = issue.get("description") or ""
    if description:
        head_lines.append("")
        head_lines.append("----")
        head_lines.extend(description.splitlines())

    parts.append(("", "\n".join(head_lines)))

    # journalを描画対象に追加
    indexed = _notes_journals(issue)
    if indexed:
        parts.append(("", "\n\n----\n"))
        parts.append(("", messages.tui_preview_comments_header + "\n"))
        edit = state.issue_tab.comment_select
        editable_set = set(edit.editable_indexes) if edit.active else set()
        focus_idx = (
            edit.editable_indexes[edit.cursor]
            if edit.active and edit.editable_indexes
            else None
        )
        for j_idx, j in indexed:
            author = (j.get("user") or {}).get("name", "")
            created = j.get("created_on", "")
            header_text = f"[{created}] {author}"
            if edit.active:
                prefix = "> " if j_idx == focus_idx else "  "
                mark = "*" if j_idx in editable_set else " "
                style = "reverse" if j_idx == focus_idx else ""
                parts.append((style, f"{prefix}{mark} {header_text}\n"))
            else:
                parts.append(("", f"{header_text}\n"))
            for note_line in (j.get("notes") or "").splitlines():
                parts.append(
                    ("", f"    {note_line}\n" if edit.active else f"  {note_line}\n")
                )

    return parts


def _status_hint(state: TuiState) -> str:
    if state.issue_tab.comment_select.active:
        return messages.tui_comment_select_status_hint
    hint = messages.tui_status_hint_issues.format(page_label=_page_label(state))
    if state.issue_tab.filter.is_active():
        hint = f" [{state.issue_tab.filter.short_label()}]" + hint
    return hint


def editable_journal_indexes(issue: Issue, me_id: str | None) -> list[int]:
    """`issue["journals"]` のうち、自分が書いた notes 付き journal の index を返す。"""
    if me_id is None:
        return []
    my_note_indexes: list[int] = []
    for i, journal in enumerate(issue.get("journals") or []):
        if not (journal.get("notes") or "").strip():
            continue
        author_id = (journal.get("user") or {}).get("id")
        if author_id is not None and str(author_id) == str(me_id):
            my_note_indexes.append(i)
    return my_note_indexes


def enter_comment_select_mode(state: TuiState):
    if not state.issue_tab.issues:
        return
    issue = state.issue_tab.issues[state.issue_tab.cursor]
    indexes = editable_journal_indexes(issue, state.me_id)
    if not indexes:
        return
    edit = state.issue_tab.comment_select
    edit.editable_indexes = indexes
    edit.cursor = len(indexes) - 1
    edit.active = True


def comment_select_cursor_up(state: TuiState) -> None:
    edit = state.issue_tab.comment_select
    if edit.active and edit.editable_indexes:
        edit.cursor = max(0, edit.cursor - 1)


def comment_select_cursor_down(state: TuiState) -> None:
    edit = state.issue_tab.comment_select
    if edit.active and edit.editable_indexes:
        edit.cursor = min(len(edit.editable_indexes) - 1, edit.cursor + 1)


def exit_comment_select_mode(state: TuiState) -> None:
    state.issue_tab.comment_select = CommentSelectState()


def selected_journal(state: TuiState) -> Journal | None:
    """選択モード中にカーソルが指している journal を返す。"""
    edit = state.issue_tab.comment_select
    if not edit.active or not edit.editable_indexes:
        return None
    if not state.issue_tab.issues:
        return None
    issue = state.issue_tab.issues[state.issue_tab.cursor]
    journals = issue.get("journals") or []
    j_idx = edit.editable_indexes[edit.cursor]
    if 0 <= j_idx < len(journals):
        return journals[j_idx]
    return None


def confirm_comment_edit(state: TuiState) -> TuiResult | None:
    """選択中の journal を編集対象とした TuiResult を返す。"""
    journal = selected_journal(state)
    if journal is None or journal.get("id") is None:
        return None
    issue_id = str(state.issue_tab.issues[state.issue_tab.cursor]["id"])
    result = TuiResult(
        action="edit_comment",
        tab="issues",
        issue_id=issue_id,
        journal_id=str(journal["id"]),
        journal_notes=journal.get("notes") or "",
        position=TuiPosition(
            offset=state.issue_tab.offset, cursor=state.issue_tab.cursor
        ),
    )
    return result


def request_comment_delete(state: TuiState) -> str | None:
    """選択中コメントの削除確認プロンプトを返す。対象が無ければ None。"""
    journal = selected_journal(state)
    if journal is None or journal.get("id") is None:
        return None
    author = (journal.get("user") or {}).get("name", "")
    created = journal.get("created_on", "")
    notes_lines = (journal.get("notes") or "").strip().splitlines()
    snippet = notes_lines[0] if notes_lines else ""
    summary = " ".join(part for part in (f"[{created}]", author, snippet) if part)
    return messages.tui_comment_delete_prompt.format(summary=summary)


def confirm_comment_delete(state: TuiState) -> TuiResult | None:
    journal = selected_journal(state)
    if journal is None or journal.get("id") is None:
        return None
    issue_id = str(state.issue_tab.issues[state.issue_tab.cursor]["id"])
    return TuiResult(
        action="delete_comment",
        tab="issues",
        issue_id=issue_id,
        journal_id=str(journal["id"]),
        position=TuiPosition(
            offset=state.issue_tab.offset, cursor=state.issue_tab.cursor
        ),
    )


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
    if not state.issue_tab.issues:
        return
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
    enter_comment_select_mode(state)


def fetch_issues_with_filter(state: TuiState, offset: int) -> IssuesPageResponse:
    f = state.issue_tab.filter
    return fetch_issues_page(
        project_id=state.effective_project_id(),
        status_id=f.status_id,
        assigned_to=f.assigned_to_id,
        tracker_id=f.tracker_id,
        query_id=f.query_id,
        limit=state.page_size,
        offset=offset,
    )


def _apply_page(state: TuiState, page: IssuesPageResponse, offset: int) -> None:
    state.issue_tab.offset = offset
    state.issue_tab.issues = page["issues"]
    state.issue_tab.total_count = page.get("total_count", len(page["issues"]))
    state.issue_tab.cursor = 0


def reload_with_filter(state: TuiState) -> None:
    """フィルタ条件で先頭ページから再取得する。filter modal からの適用で呼ぶ。"""
    _apply_page(state, fetch_issues_with_filter(state, 0), 0)


def _on_reload(state: TuiState) -> None:
    """現在のフィルタ・ページのまま再取得する。カーソル位置はクランプして保持する。"""
    prev_cursor = state.issue_tab.cursor
    page = fetch_issues_with_filter(state, state.issue_tab.offset)
    state.issue_tab.issues = page["issues"]
    state.issue_tab.total_count = page.get("total_count", len(page["issues"]))
    if state.issue_tab.issues:
        state.issue_tab.cursor = max(
            0, min(prev_cursor, len(state.issue_tab.issues) - 1)
        )
    else:
        state.issue_tab.cursor = 0


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
    webbrowser.open(f"{config.redmine_url}/issues/{issue_id}")


def _on_open_web_by_id(state: TuiState, target_id: int) -> None:
    webbrowser.open(f"{config.redmine_url}/issues/{target_id}")


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
        if not state.issue_tab.issues:
            return None
        return _exit_result(state, "update")
    if key == "c":
        return _exit_result(state, "create", issue_id="")
    if key == "n":
        if not state.issue_tab.issues:
            return None
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
    ("  Ctrl+E / Ctrl+Y", messages.tui_help_preview_scroll_line),
    ("  Ctrl+D / Ctrl+U", messages.tui_help_preview_scroll_half_page),
    (messages.tui_help_section_search, ""),
    ("  /", messages.tui_help_start_search),
    ("  n / N", messages.tui_help_next_prev_match),
    (messages.tui_help_section_filter, ""),
    ("  f", messages.tui_help_filter_issues),
    ("  p", messages.tui_help_switch_project),
    ("  P", messages.tui_help_switch_profile),
    (messages.tui_help_section_actions, ""),
    ("  Enter", messages.tui_help_issue_load_comments),
    ("  jk / u / D / Esc", messages.tui_help_issue_comment_select_in_mode),
    ("  c / u", messages.tui_help_issue_create_or_update),
    ("  n", messages.tui_help_issue_add_comment),
    ("  t", messages.tui_help_issue_create_time_entry),
    ("  D", messages.tui_help_issue_delete),
    ("  v / <N>V", messages.tui_help_issue_open_web_or_n),
    ("  R", messages.tui_help_reload),
    (messages.tui_help_section_other, ""),
    ("  ?", messages.tui_help_show_or_close),
    ("  q / Ctrl+C", messages.tui_help_quit),
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
    on_reload=_on_reload,
    on_action_key=_on_action_key,
    on_search=_on_search,
    get_cursor_y=lambda state: state.issue_tab.cursor,
    help_lines=_HELP_LINES,
)
