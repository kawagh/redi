import webbrowser

import requests

from redi.api.wiki import fetch_wiki, fetch_wikis, flatten_wiki_tree
from redi.config import default_project_id, redmine_url, wiki_project_id
from redi.tui.render import render_meta_table
from redi.tui.state import (
    Renderable,
    TuiAction,
    TuiPosition,
    TuiResult,
    TuiState,
)
from redi.tui.tab import TabView, noop


def _wiki_project() -> str | None:
    return wiki_project_id or default_project_id


def _load_wikis(state: TuiState) -> None:
    if state.wiki_tab.loaded:
        return
    state.wiki_tab.loaded = True
    project = _wiki_project()
    if not project:
        state.wiki_tab.error = (
            "wiki_project_id か default_project_id を設定してください"
        )
        return
    try:
        pages = fetch_wikis(project)
    except requests.exceptions.RequestException as e:
        state.wiki_tab.error = f"Wikiの取得に失敗しました: {e}"
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
        state.wiki_tab.texts[title] = f"(読み込みに失敗しました: {e})"
        return
    if wiki is None:
        state.wiki_tab.texts[title] = "(ページが見つかりません)"
        return
    state.wiki_tab.texts[title] = wiki.get("text", "") or ""


def _render_list(state: TuiState) -> Renderable:
    if state.wiki_tab.error:
        return [("", state.wiki_tab.error)]
    if not state.wiki_tab.labels:
        if state.wiki_tab.loaded:
            return [("", "Wikiページが見つかりません")]
        return [("", "(Wikiを読み込み中...)")]
    result: Renderable = []
    for i, label in enumerate(state.wiki_tab.labels):
        prefix = "> " if i == state.wiki_tab.cursor else "  "
        result.append(("", f"{prefix}{label}\n"))
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
        ("親", (page.get("parent") or {}).get("title", "")),
        ("バージョン", str(page.get("version", "")) if page.get("version") else ""),
        ("作成", page.get("created_on") or ""),
        ("更新", page.get("updated_on") or ""),
    ]
    lines.extend(render_meta_table(meta))

    text = state.wiki_tab.texts.get(title)
    lines.append("")
    lines.append("----")
    if text is None:
        lines.append("(Enter で本文をロード)")
    else:
        lines.extend(text.splitlines())
    return [("", "\n".join(lines))]


def _status_hint(state: TuiState) -> str:
    return " ↑↓/jk:移動 Enter:本文ロード c:作成 u:更新 v:web Tab:タブ切替 q:終了 "


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


def _on_open_web(state: TuiState) -> None:
    if not state.wiki_tab.pages:
        return
    project = _wiki_project()
    if not project:
        return
    title = state.wiki_tab.pages[state.wiki_tab.cursor].get("title")
    if title:
        webbrowser.open(f"{redmine_url}/projects/{project}/wiki/{title}")


WIKI_TAB = TabView(
    label="Wiki",
    render_list=_render_list,
    render_preview=_render_preview,
    status_hint=_status_hint,
    on_up=_on_up,
    on_down=_on_down,
    on_enter=_on_enter,
    on_page_forward=noop,
    on_page_backward=noop,
    on_open_web=_on_open_web,
    on_activate=_load_wikis,
    on_action_key=_on_action_key,
    get_cursor_y=lambda state: state.wiki_tab.cursor,
)
