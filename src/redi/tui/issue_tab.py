import webbrowser

from redi.api.issue import fetch_issue, fetch_issues
from redi.config import default_project_id, redmine_url
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
        ("ステータス", named("status")),
        ("優先度", named("priority")),
        ("トラッカー", named("tracker")),
        ("担当者", named("assigned_to")),
        ("作成者", named("author")),
        ("開始日", issue.get("start_date") or ""),
        ("期日", issue.get("due_date") or ""),
        (
            "進捗",
            f"{issue['done_ratio']}%" if issue.get("done_ratio") is not None else "",
        ),
        (
            "予定工数",
            f"{issue['estimated_hours']} h"
            if issue.get("estimated_hours") is not None
            else "",
        ),
        (
            "作業時間",
            f"{issue['spent_hours']} h" if issue.get("spent_hours") is not None else "",
        ),
        ("作成", issue.get("created_on") or ""),
        ("更新", issue.get("updated_on") or ""),
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
        lines.append("コメント:")
        for j in notes:
            author = (j.get("user") or {}).get("name", "")
            created = j.get("created_on", "")
            lines.append(f"[{created}] {author}")
            for nl in (j.get("notes") or "").splitlines():
                lines.append(f"  {nl}")

    return [("", "\n".join(lines))]


def _status_hint(state: TuiState) -> str:
    page = state.issue_tab.offset // state.page_size + 1
    return (
        f" Page {page} (offset={state.issue_tab.offset})  "
        "jk:移動 /:検索 c:作成 u:更新 v:web ?:ヘルプ q:終了 "
    )


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


def _on_page_forward(state: TuiState) -> None:
    next_issues = fetch_issues(
        project_id=default_project_id,
        limit=state.page_size,
        offset=state.issue_tab.offset + state.page_size,
    )
    if next_issues:
        state.issue_tab.offset += state.page_size
        state.issue_tab.issues = next_issues
        state.issue_tab.cursor = 0


def _on_page_backward(state: TuiState) -> None:
    if state.issue_tab.offset <= 0:
        return
    state.issue_tab.offset = max(0, state.issue_tab.offset - state.page_size)
    state.issue_tab.issues = fetch_issues(
        project_id=default_project_id,
        limit=state.page_size,
        offset=state.issue_tab.offset,
    )
    state.issue_tab.cursor = 0


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
    ("移動", ""),
    ("  ↑/k/Ctrl+P", "上へ"),
    ("  ↓/j/Ctrl+N", "下へ"),
    ("  gg / G", "先頭 / 末尾へ"),
    ("  <N>G", "#N のイシューへジャンプ"),
    ("  ←/h / →/l", "前ページ / 次ページ"),
    ("  Tab / Shift+Tab", "タブ切替 (次 / 前)"),
    ("検索", ""),
    ("  /", "検索開始"),
    ("  n / N", "次 / 前の検索結果"),
    ("アクション", ""),
    ("  Enter", "選択イシューのコメントを読込"),
    ("  c / u", "イシュー作成 / 更新"),
    ("  n", "コメント追加 (検索クエリ未設定時)"),
    ("  t", "時間記録の作成"),
    ("  v / <N>V", "選択イシューを web で開く / #N を web で開く"),
    ("その他", ""),
    ("  ?", "このヘルプを表示 / 閉じる"),
    ("  q / Esc / Ctrl+C", "終了"),
]


ISSUE_TAB = TabView(
    label="イシュー",
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
