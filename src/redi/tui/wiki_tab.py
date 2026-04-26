import webbrowser

import requests

from redi.api.wiki import fetch_wiki, fetch_wikis, flatten_wiki_tree
from redi.config import default_project_id, redmine_url, wiki_project_id
from redi.i18n import messages
from redi.tui.render import highlight_segments, render_meta_table
from redi.tui.state import (
    Renderable,
    TuiAction,
    TuiPosition,
    TuiResult,
    TuiState,
)
from redi.tui.tab import TabView, noop, noop_jump


def _wiki_project() -> str | None:
    return wiki_project_id or default_project_id


def _load_wikis(state: TuiState) -> None:
    if state.wiki_tab.loaded:
        return
    state.wiki_tab.loaded = True
    project = _wiki_project()
    if not project:
        state.wiki_tab.error = messages.tui_wiki_project_required
        return
    try:
        pages = fetch_wikis(project)
    except requests.exceptions.RequestException as e:
        state.wiki_tab.error = messages.tui_wiki_load_failed.format(error=e)
        return
    items = flatten_wiki_tree(pages)
    state.wiki_tab.pages = [page for page, _ in items]
    state.wiki_tab.labels = [
        f"{tree_prefix}{page['title']}" for page, tree_prefix in items
    ]
    state.wiki_tab.cursor = 0


def _load_wiki_text(state: TuiState, title: str) -> None:
    if title in state.wiki_tab.texts:
        return
    project = _wiki_project()
    if not project:
        return
    try:
        wiki = fetch_wiki(project, title)
    except requests.exceptions.RequestException as e:
        state.wiki_tab.texts[title] = messages.tui_wiki_load_text_failed.format(error=e)
        return
    if wiki is None:
        state.wiki_tab.texts[title] = messages.tui_wiki_page_missing
        return
    state.wiki_tab.texts[title] = wiki.get("text", "") or ""


def _render_list(state: TuiState) -> Renderable:
    if state.wiki_tab.error:
        return [("", state.wiki_tab.error)]
    if not state.wiki_tab.labels:
        if state.wiki_tab.loaded:
            return [("", messages.tui_wiki_no_pages)]
        return [("", messages.tui_wiki_loading)]
    result: Renderable = []
    query = state.search_query
    for i, label in enumerate(state.wiki_tab.labels):
        prefix = "> " if i == state.wiki_tab.cursor else "  "
        text = f"{prefix}{label}"
        result.extend(highlight_segments(text, query))
        result.append(("", "\n"))
    return result


def _render_preview(state: TuiState) -> Renderable:
    if state.wiki_tab.error:
        return [("", state.wiki_tab.error)]
    if not state.wiki_tab.pages:
        return [("", "")]
    page = state.wiki_tab.pages[state.wiki_tab.cursor]
    title = page.get("title", "")
    lines = [title, ""]
    meta = [
        (messages.tui_meta_parent, (page.get("parent") or {}).get("title", "")),
        (
            messages.tui_meta_version,
            str(page.get("version", "")) if page.get("version") else "",
        ),
        (messages.tui_meta_created, page.get("created_on") or ""),
        (messages.tui_meta_updated, page.get("updated_on") or ""),
    ]
    lines.extend(render_meta_table(meta))

    text = state.wiki_tab.texts.get(title)
    lines.append("")
    lines.append("----")
    if text is None:
        lines.append(messages.tui_wiki_press_enter_to_load)
    else:
        lines.extend(text.splitlines())
    return [("", "\n".join(lines))]


def _status_hint(state: TuiState) -> str:
    return messages.tui_status_hint_wiki


def _exit_result(
    state: TuiState,
    action: TuiAction,
    wiki_title: str | None = None,
    parent_wiki_title: str | None = None,
) -> TuiResult:
    if wiki_title is None and state.wiki_tab.pages:
        wiki_title = state.wiki_tab.pages[state.wiki_tab.cursor].get("title")
    return TuiResult(
        action=action,
        tab="wiki",
        wiki_title=wiki_title,
        parent_wiki_title=parent_wiki_title,
        position=TuiPosition(cursor=state.wiki_tab.cursor),
    )


def _on_up(state: TuiState) -> None:
    state.wiki_tab.cursor = max(0, state.wiki_tab.cursor - 1)


def _on_down(state: TuiState) -> None:
    if state.wiki_tab.pages:
        state.wiki_tab.cursor = min(
            len(state.wiki_tab.pages) - 1, state.wiki_tab.cursor + 1
        )


def _on_goto_top(state: TuiState) -> None:
    if state.wiki_tab.pages:
        state.wiki_tab.cursor = 0


def _on_goto_bottom(state: TuiState) -> None:
    if state.wiki_tab.pages:
        state.wiki_tab.cursor = len(state.wiki_tab.pages) - 1


def _on_enter(state: TuiState) -> None:
    if not state.wiki_tab.pages:
        return
    title = state.wiki_tab.pages[state.wiki_tab.cursor].get("title")
    if title:
        _load_wiki_text(state, title)


def _on_action_key(state: TuiState, key: str) -> TuiResult | None:
    if key == "c":
        parent = None
        if state.wiki_tab.pages:
            parent = state.wiki_tab.pages[state.wiki_tab.cursor].get("title")
        return _exit_result(state, "create", parent_wiki_title=parent)
    if key == "u":
        if not state.wiki_tab.pages:
            return None
        return _exit_result(state, "update")
    return None


def _on_search(state: TuiState, query: str, forward: bool = True) -> None:
    if not query:
        return
    labels = state.wiki_tab.labels
    if not labels:
        return
    targets = [label.lower() for label in labels]
    query_lower = query.lower()
    n = len(labels)
    step = 1 if forward else -1
    start = (state.wiki_tab.cursor + step) % n
    for i in range(n):
        idx = (start + step * i) % n
        if query_lower in targets[idx]:
            state.wiki_tab.cursor = idx
            return


def _on_open_web(state: TuiState) -> None:
    if not state.wiki_tab.pages:
        return
    project = _wiki_project()
    if not project:
        return
    title = state.wiki_tab.pages[state.wiki_tab.cursor].get("title")
    if title:
        webbrowser.open(f"{redmine_url}/projects/{project}/wiki/{title}")


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
    ("  Enter", messages.tui_help_wiki_load_text),
    ("  c", messages.tui_help_wiki_create_child),
    ("  u", messages.tui_help_wiki_update_page),
    ("  v", messages.tui_help_wiki_open_web),
    (messages.tui_help_section_other, ""),
    ("  ?", messages.tui_help_show_or_close),
    ("  q / Esc / Ctrl+C", messages.tui_help_quit),
]


WIKI_TAB = TabView(
    label=messages.tui_tab_label_wiki,
    render_list=_render_list,
    render_preview=_render_preview,
    status_hint=_status_hint,
    on_up=_on_up,
    on_down=_on_down,
    on_goto_top=_on_goto_top,
    on_goto_bottom=_on_goto_bottom,
    on_jump_to_id=noop_jump,
    on_enter=_on_enter,
    on_page_forward=noop,
    on_page_backward=noop,
    on_open_web=_on_open_web,
    on_open_web_by_id=noop_jump,
    on_activate=_load_wikis,
    on_action_key=_on_action_key,
    on_search=_on_search,
    get_cursor_y=lambda state: state.wiki_tab.cursor,
    help_lines=_HELP_LINES,
)
