import webbrowser

import requests

from redi import config
from redi.api.time_entry import TimeEntry, TimeEntryNotFoundException
from redi.i18n import messages
from redi.service import time_entry_service
from redi.text_format import highlight_segments, render_meta_table
from redi.tui.state import (
    Renderable,
    TuiPosition,
    TuiResult,
    TuiState,
    realign_page,
)
from redi.tui.tab import TabView, noop, noop_jump


def _fetch_page_with_subjects(state: TuiState, offset: int) -> dict:
    """`offset` から始まる 1 ページ分の time_entries と issue subjects をまとめて返す。"""
    page = time_entry_service.fetch_page(
        project_id=state.effective_project_id(),
        user_id=state.time_entry_tab.filter.user_id,
        limit=state.page_size,
        offset=offset,
    )
    entries = page["time_entries"]
    try:
        subjects = time_entry_service.fetch_issue_subjects(entries)
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


def _in_summary(state: TuiState) -> bool:
    return state.time_entry_tab.summary.show


def _load_summary(state: TuiState) -> None:
    """一覧と同じ条件 (プロジェクト・ユーザー) の作業時間を全件取って集計し直す。"""
    view = state.time_entry_tab.summary
    view.error = None
    try:
        entries = time_entry_service.fetch_all(
            project_id=state.effective_project_id(),
            user_id=state.time_entry_tab.filter.user_id,
        )
    except requests.exceptions.RequestException as e:
        view.error = messages.tui_time_entry_load_failed.format(error=e)
        view.summary = None
        return
    try:
        subjects = time_entry_service.fetch_issue_subjects(entries)
    except requests.exceptions.RequestException:
        subjects = {}
    view.summary = time_entry_service.summarize_by_date(entries)
    view.issue_subjects = subjects
    view.cursor = min(view.cursor, _max_summary_cursor(state))


def toggle_summary(state: TuiState) -> None:
    """一覧と集計ビューを切り替える。集計ビューに入るたびに全件を取り直す。"""
    view = state.time_entry_tab.summary
    if view.show:
        view.show = False
        return
    view.show = True
    view.cursor = 0
    _load_summary(state)


def _ticket_label(te: TimeEntry, subjects: dict[int, str]) -> str:
    issue_id = (te.get("issue") or {}).get("id")
    if issue_id:
        subject = subjects.get(issue_id)
        return f"#{issue_id} {subject}" if subject else f"#{issue_id}"
    return (te.get("project") or {}).get("name", "")


def _summary_lines(state: TuiState) -> list[str]:
    """集計ビューの行。先頭に合計、続けて日付ごとの合計とその日の作業時間を並べる。"""
    view = state.time_entry_tab.summary
    if view.error:
        return [view.error]
    summary = view.summary
    if summary is None:
        return [messages.tui_time_entry_summary_loading]
    if summary.count == 0:
        return [messages.tui_time_entry_no_entries]
    fmt = time_entry_service.format_hours
    entries = [te for day in summary.days for te in day.entries]
    id_width = max(len(f"#{te['id']}") for te in entries)
    hours_width = max(len(fmt(te["hours"])) for te in entries)
    lines = [
        messages.tui_time_entry_summary_total.format(
            hours=fmt(summary.total_hours), count=summary.count
        )
    ]
    for day in summary.days:
        lines.append(f"{day.spent_on}  {fmt(day.hours)}h")
        for te in day.entries:
            ticket = _ticket_label(te, view.issue_subjects)
            lines.append(
                f"    {f'#{te["id"]}':<{id_width}}  "
                f"{fmt(te['hours']):>{hours_width}}h  {ticket}".rstrip()
            )
    return lines


def _max_summary_cursor(state: TuiState) -> int:
    return max(0, len(_summary_lines(state)) - 1)


def _move_summary_cursor(state: TuiState, delta: int) -> None:
    view = state.time_entry_tab.summary
    view.cursor = max(0, min(view.cursor + delta, _max_summary_cursor(state)))


def _render_summary(state: TuiState) -> Renderable:
    cursor = state.time_entry_tab.summary.cursor
    result: Renderable = []
    for i, line in enumerate(_summary_lines(state)):
        prefix = "> " if i == cursor else "  "
        result.append(("", f"{prefix}{line}\n"))
    return result


def _render_list(state: TuiState) -> Renderable:
    if _in_summary(state):
        return _render_summary(state)
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
        line = time_entry_service.format_time_entry_line(te, issue_subjects=subjects)
        result.extend(highlight_segments(f"{prefix}{line}", query))
        result.append(("", "\n"))
    return result


def _render_preview(state: TuiState) -> Renderable:
    if _in_summary(state):
        return [("", "")]
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
            messages.meta_project,
            f"{project.get('name', '')} (id={project.get('id', '')})",
        ),
        (
            messages.meta_user,
            f"{user.get('name', '')} (id={user.get('id', '')})",
        ),
        (messages.meta_activity, (te.get("activity") or {}).get("name", "")),
        (messages.meta_issue, ticket_cell),
        (messages.meta_created, te.get("created_on") or ""),
        (messages.meta_updated, te.get("updated_on") or ""),
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
    if _in_summary(state):
        hint = messages.tui_status_hint_time_entry_summary
    else:
        hint = messages.tui_status_hint_time_entries.format(
            page_label=_page_label(state)
        )
    if state.time_entry_tab.filter.is_active():
        hint = f" [{state.time_entry_tab.filter.short_label()}]" + hint
    return hint


def reload_with_filter(state: TuiState) -> None:
    """フィルタ条件で先頭ページから取得し直す。フィルタダイアログの適用で呼ぶ。

    集計ビューを表示中なら、集計も新しい条件で取り直す。
    """
    if _in_summary(state):
        _load_summary(state)
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
    # 集計ビューには選択行が無いので、行を対象にする操作は効かせない
    if _in_summary(state):
        return None
    if key == "c":
        entries = state.time_entry_tab.entries
        issue_id: int | None = None
        if entries:
            te = entries[state.time_entry_tab.cursor]
            cursor_issue_id = (te.get("issue") or {}).get("id")
            if cursor_issue_id is not None:
                issue_id = cursor_issue_id
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
            time_entry_id=te["id"],
            position=TuiPosition(
                offset=state.time_entry_tab.offset,
                cursor=state.time_entry_tab.cursor,
            ),
        )
    return None


def _on_up(state: TuiState) -> None:
    if _in_summary(state):
        _move_summary_cursor(state, -1)
        return
    state.time_entry_tab.cursor = max(0, state.time_entry_tab.cursor - 1)


def _on_down(state: TuiState) -> None:
    if _in_summary(state):
        _move_summary_cursor(state, 1)
        return
    if state.time_entry_tab.entries:
        state.time_entry_tab.cursor = min(
            len(state.time_entry_tab.entries) - 1,
            state.time_entry_tab.cursor + 1,
        )


def _on_goto_top(state: TuiState) -> None:
    if _in_summary(state):
        state.time_entry_tab.summary.cursor = 0
        return
    if state.time_entry_tab.entries:
        state.time_entry_tab.cursor = 0


def _on_goto_bottom(state: TuiState) -> None:
    if _in_summary(state):
        state.time_entry_tab.summary.cursor = _max_summary_cursor(state)
        return
    if state.time_entry_tab.entries:
        state.time_entry_tab.cursor = len(state.time_entry_tab.entries) - 1


def _on_search(state: TuiState, query: str, forward: bool = True) -> None:
    if not query or _in_summary(state):
        return
    entries = state.time_entry_tab.entries
    if not entries:
        return
    subjects = state.time_entry_tab.issue_subjects
    targets = [
        time_entry_service.format_time_entry_line(te, issue_subjects=subjects).lower()
        for te in entries
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
    """カーソル行の削除確認プロンプトを返す。対象がなければ None。

    集計ビューでは選択行が見えないので削除させない。
    """
    entries = state.time_entry_tab.entries
    if not entries or _in_summary(state):
        return None
    te = entries[state.time_entry_tab.cursor]
    summary = time_entry_service.format_time_entry_line(
        te, issue_subjects=state.time_entry_tab.issue_subjects
    )
    return messages.tui_time_entry_delete_prompt.format(summary=summary)


def apply_deleted(state: TuiState, cursor: int) -> None:
    """削除済みの行を一覧から取り除き、total_count と cursor を整える。"""
    entries = state.time_entry_tab.entries
    entries.pop(cursor)
    state.time_entry_tab.total_count = max(0, state.time_entry_tab.total_count - 1)
    if cursor >= len(entries):
        state.time_entry_tab.cursor = max(0, len(entries) - 1)


def confirm_delete(state: TuiState) -> None:
    """カーソル行の time_entry を削除する。失敗時は flash_message に理由を出す。"""
    entries = state.time_entry_tab.entries
    if not entries:
        return
    cursor = state.time_entry_tab.cursor
    te = entries[cursor]
    try:
        time_entry_service.delete_time_entry(te["id"])
    except TimeEntryNotFoundException:
        state.flash_message = messages.tui_time_entry_delete_missing.format(id=te["id"])
        return
    except requests.exceptions.RequestException as e:
        state.flash_message = messages.tui_time_entry_delete_failed.format(error=e)
        return
    apply_deleted(state, cursor)


def _on_reload(state: TuiState) -> None:
    """現在のページのまま time_entry 一覧を取り直す。

    同じ id の entry が残っていればその位置に cursor を復元し、無ければ
    元の cursor 位置を新一覧の範囲内にクランプする。集計ビューを表示中なら
    集計を取り直す。
    """
    if _in_summary(state):
        _load_summary(state)
        return
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


def _on_resize(state: TuiState) -> None:
    """新しい page_size でページを取り直す。選択していた entry は選ばれたまま保つ。

    offset を新しい page_size のページ境界へ揃えるので、リサイズ後も
    ステータスバーの Page 表示と実データが一致する。通信エラーは呼び出し元
    (ResizeWatcher) に投げ、失敗時は一覧を書き換えない。
    """
    offset, cursor = realign_page(
        state.time_entry_tab.offset, state.time_entry_tab.cursor, state.page_size
    )
    page = _fetch_page_with_subjects(state, offset)
    state.time_entry_tab.offset = offset
    state.time_entry_tab.entries = page["time_entries"]
    state.time_entry_tab.total_count = page["total_count"]
    state.time_entry_tab.issue_subjects = page["issue_subjects"]
    state.time_entry_tab.cursor = min(
        cursor, max(0, len(state.time_entry_tab.entries) - 1)
    )


def _on_page_forward(state: TuiState) -> None:
    if _in_summary(state):
        _move_summary_cursor(state, state.page_size)
        return
    next_offset = state.time_entry_tab.offset + state.page_size
    try:
        page = _fetch_page_with_subjects(state, next_offset)
    except requests.exceptions.RequestException as e:
        state.time_entry_tab.error = messages.tui_time_entry_load_failed.format(error=e)
        return
    if page["time_entries"]:
        _apply_page(state, page, next_offset)


def _on_page_backward(state: TuiState) -> None:
    if _in_summary(state):
        _move_summary_cursor(state, -state.page_size)
        return
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
    if not entries or _in_summary(state):
        return
    te = entries[state.time_entry_tab.cursor]
    issue_id = (te.get("issue") or {}).get("id")
    if issue_id:
        webbrowser.open(f"{config.redmine_url}/issues/{issue_id}")
    else:
        webbrowser.open(f"{config.redmine_url}/time_entries")


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
    ("  Esc", messages.tui_help_clear_search),
    (messages.tui_help_section_filter, ""),
    ("  f", messages.tui_help_filter_user),
    ("  p", messages.tui_help_switch_project),
    ("  P", messages.tui_help_switch_profile),
    (messages.tui_help_section_actions, ""),
    ("  c", messages.tui_help_time_entry_create),
    ("  u", messages.tui_help_time_entry_update),
    ("  D", messages.tui_help_time_entry_delete),
    ("  v", messages.tui_help_time_entry_open_web),
    ("  V", messages.tui_help_time_entry_toggle_summary),
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
    on_resize=_on_resize,
    on_action_key=_on_action_key,
    on_search=_on_search,
    get_cursor_y=lambda state: (
        state.time_entry_tab.summary.cursor
        if _in_summary(state)
        else state.time_entry_tab.cursor
    ),
    help_lines=_HELP_LINES,
)
