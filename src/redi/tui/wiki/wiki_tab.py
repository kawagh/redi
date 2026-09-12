import webbrowser

import requests

from redi.api.wiki import WikiPage
from redi.i18n import messages
from redi.service import wiki_service
from redi.text_format import highlight_segments, render_meta_table
from redi.tui.state import (
    Renderable,
    TuiAction,
    TuiPosition,
    TuiResult,
    TuiState,
    WikiDiffView,
    WikiVersionView,
)
from redi.tui.tab import TabView, noop, noop_jump


def _wiki_project(state: TuiState) -> str | None:
    return state.effective_wiki_project_id()


def current_page(state: TuiState) -> WikiPage | None:
    """カーソル位置のページ。一覧が空なら None。"""
    pages = state.wiki_tab.pages
    if not pages:
        return None
    return pages[state.wiki_tab.cursor]


def viewing_version(state: TuiState) -> WikiVersionView | None:
    """カーソル位置のページで過去版を表示中ならその内容。最新版なら None。

    `version_view` は別ページへ移っても残り得るので、タイトルが一致するときだけ有効とみなす。
    """
    view = state.wiki_tab.version_view
    page = current_page(state)
    if view is None or page is None or page.get("title") != view.title:
        return None
    return view


def viewing_diff(state: TuiState) -> WikiDiffView | None:
    """カーソル位置のページで差分を表示中ならその 2 版。本文表示なら None。"""
    view = state.wiki_tab.diff_view
    page = current_page(state)
    if view is None or page is None or page.get("title") != view.title:
        return None
    return view


def _set_cursor(state: TuiState, index: int) -> None:
    """カーソルを動かす。別ページへ移ったら過去版と差分の表示はやめて最新版に戻す。"""
    if index != state.wiki_tab.cursor:
        state.wiki_tab.version_view = None
        state.wiki_tab.diff_view = None
    state.wiki_tab.cursor = index


def set_pages(state: TuiState, pages: list[WikiPage]) -> None:
    """ページ一覧を差し替え、ツリー順とその表示ラベルを作り直す。

    ページが増減すればツリーの装飾も変わるため、pages と labels は必ずここで揃える。
    """
    items = wiki_service.flatten_wiki_tree(pages)
    state.wiki_tab.pages = [page for page, _ in items]
    state.wiki_tab.labels = [
        f"{tree_prefix}{page['title']}" for page, tree_prefix in items
    ]


def _load_wikis(state: TuiState) -> None:
    if state.wiki_tab.loaded:
        return
    state.wiki_tab.loaded = True
    project = _wiki_project(state)
    if not project:
        state.wiki_tab.error = messages.tui_wiki_project_required
        return
    try:
        pages = wiki_service.list_pages(project)
    except requests.exceptions.RequestException as e:
        state.wiki_tab.error = messages.tui_wiki_load_failed.format(error=e)
        return
    set_pages(state, pages)
    state.wiki_tab.cursor = 0


def _load_wiki_text(state: TuiState, title: str) -> None:
    if title in state.wiki_tab.texts:
        return
    project = _wiki_project(state)
    if not project:
        return
    try:
        wiki = wiki_service.read_page(project, title)
    except requests.exceptions.RequestException as e:
        state.wiki_tab.texts[title] = messages.tui_wiki_load_text_failed.format(error=e)
        return
    if wiki is None:
        state.wiki_tab.texts[title] = messages.tui_wiki_page_missing
        return
    state.wiki_tab.texts[title] = wiki.get("text", "") or ""


def load_version_text(
    state: TuiState, title: str, version: int, latest: int
) -> str | None:
    """`title` の `version` の本文をキャッシュ経由で返す。取得できなければ flash に出して None。

    最新版は Enter と同じ `texts`、過去版は `version_texts` に載せる。
    """
    if version == latest:
        _load_wiki_text(state, title)
        return state.wiki_tab.texts.get(title)
    text = state.wiki_tab.version_texts.get((title, version))
    if text is not None:
        return text
    project = _wiki_project(state)
    if not project:
        state.flash_message = messages.tui_wiki_project_required
        return None
    try:
        wiki = wiki_service.read_page(project, title, version=version)
    except requests.exceptions.RequestException as e:
        state.flash_message = messages.tui_wiki_version_load_failed.format(
            version=version, error=e
        )
        return None
    if wiki is None:
        state.flash_message = messages.tui_wiki_version_missing.format(
            title=title, version=version
        )
        return None
    text = wiki.get("text", "") or ""
    state.wiki_tab.version_texts[(title, version)] = text
    return text


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
    page = current_page(state)
    if page is None:
        return [("", "")]
    title = page.get("title", "")
    lines = [title, ""]
    view = viewing_version(state)
    if view is not None:
        # 過去版を開いていることをメタ表でも示し、最新版がいくつかを併記する
        version_label = messages.tui_wiki_meta_version_of_latest.format(
            version=view.version, latest=view.latest
        )
    else:
        latest = page.get("version")
        version_label = str(latest) if latest else ""
    meta = [
        (messages.meta_parent, (page.get("parent") or {}).get("title", "")),
        (messages.meta_version, version_label),
        (messages.meta_created, page.get("created_on") or ""),
        (messages.meta_updated, page.get("updated_on") or ""),
    ]
    lines.extend(render_meta_table(meta))

    lines.append("")
    lines.append("----")
    diff = viewing_diff(state)
    if diff is not None:
        return _render_diff(state, diff, lines)
    text = view.text if view is not None else state.wiki_tab.texts.get(title)
    if text is None:
        lines.append(messages.tui_wiki_press_enter_to_load)
    else:
        lines.extend(text.splitlines())
    return [("", "\n".join(lines))]


def _cached_text(state: TuiState, title: str, version: int) -> str | None:
    """キャッシュにある本文。最新版は `texts`、過去版は `version_texts` から引く。"""
    page = current_page(state)
    if page is not None and page.get("version") == version:
        return state.wiki_tab.texts.get(title)
    return state.wiki_tab.version_texts.get((title, version))


def _render_diff(state: TuiState, view: WikiDiffView, header: list[str]) -> Renderable:
    """選んだ 2 版の差分を比較前 → 比較後の向きで出す。本文は選択時にキャッシュへ載せてある。"""
    result: Renderable = [("", "\n".join(header) + "\n")]
    old = _cached_text(state, view.title, view.from_version)
    new = _cached_text(state, view.title, view.to_version)
    if old is None or new is None:
        result.append(("", messages.tui_wiki_press_enter_to_load))
        return result
    diff = wiki_service.diff_texts(old, new, view.from_version, view.to_version)
    if not diff:
        result.append(("", messages.tui_wiki_diff_no_changes))
        return result
    for line in diff.splitlines():
        result.append((_diff_line_style(line), line + "\n"))
    return result


def _diff_line_style(line: str) -> str:
    if line.startswith(("+++", "---")):
        return "bold"
    if line.startswith("+"):
        return "fg:ansigreen"
    if line.startswith("-"):
        return "fg:ansired"
    if line.startswith("@@"):
        return "fg:ansicyan"
    return ""


def _status_hint(state: TuiState) -> str:
    hint = messages.tui_status_hint_wiki
    diff = viewing_diff(state)
    if diff is not None:
        label = messages.tui_status_wiki_diff_active.format(
            from_version=diff.from_version, to_version=diff.to_version
        )
        return f" [{label}]" + hint
    view = viewing_version(state)
    if view is None:
        return hint
    # 過去版を開いている間は、編集や削除の前に気付けるようステータスバーにも出す
    label = messages.tui_status_wiki_version_active.format(
        version=view.version, latest=view.latest
    )
    return f" [{label}]" + hint


def _exit_result(
    state: TuiState,
    action: TuiAction,
    wiki_title: str | None = None,
    parent_wiki_title: str | None = None,
) -> TuiResult:
    page = current_page(state)
    if wiki_title is None and page is not None:
        wiki_title = page.get("title")
    return TuiResult(
        action=action,
        tab="wiki",
        wiki_title=wiki_title,
        parent_wiki_title=parent_wiki_title,
        position=TuiPosition(cursor=state.wiki_tab.cursor),
    )


def _on_up(state: TuiState) -> None:
    _set_cursor(state, max(0, state.wiki_tab.cursor - 1))


def _on_down(state: TuiState) -> None:
    if state.wiki_tab.pages:
        _set_cursor(
            state, min(len(state.wiki_tab.pages) - 1, state.wiki_tab.cursor + 1)
        )


def _on_goto_top(state: TuiState) -> None:
    if state.wiki_tab.pages:
        _set_cursor(state, 0)


def _on_goto_bottom(state: TuiState) -> None:
    if state.wiki_tab.pages:
        _set_cursor(state, len(state.wiki_tab.pages) - 1)


def _on_enter(state: TuiState) -> None:
    page = current_page(state)
    if page is None:
        return
    title = page.get("title")
    if title:
        _load_wiki_text(state, title)


def _on_action_key(state: TuiState, key: str) -> TuiResult | None:
    page = current_page(state)
    if key == "c":
        parent = page.get("title") if page is not None else None
        return _exit_result(state, "create", parent_wiki_title=parent)
    if key == "u":
        if page is None:
            return None
        if viewing_version(state) is not None:
            # 過去版の本文で更新画面を開くと、古い内容で最新版を上書きしてしまう
            state.flash_message = messages.tui_wiki_version_readonly
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
            _set_cursor(state, idx)
            return


def _on_reload(state: TuiState) -> None:
    """Wiki ページ一覧と読込済み本文をクリアして取り直す。

    `loaded` を立てたままだと `_load_wikis` が早期 return するので一度倒す。
    既存のカーソル位置はタイトル一致で復元を試み、無ければ先頭に戻る。
    """
    prev_page = current_page(state)
    prev_title = prev_page.get("title") if prev_page is not None else None
    state.wiki_tab.loaded = False
    state.wiki_tab.error = None
    state.wiki_tab.pages = []
    state.wiki_tab.labels = []
    state.wiki_tab.texts = {}
    state.wiki_tab.version_texts = {}
    state.wiki_tab.version_view = None
    state.wiki_tab.diff_view = None
    state.wiki_tab.cursor = 0
    _load_wikis(state)
    if prev_title is not None:
        for i, page in enumerate(state.wiki_tab.pages):
            if page.get("title") == prev_title:
                state.wiki_tab.cursor = i
                return


def _on_open_web(state: TuiState) -> None:
    page = current_page(state)
    if page is None:
        return
    project = _wiki_project(state)
    if not project:
        return
    title = page.get("title")
    if not title:
        return
    # 差分表示中は Redmine の diff 画面、過去版を開いていれば同じ版を web でも出す
    diff = viewing_diff(state)
    if diff is not None:
        webbrowser.open(
            wiki_service.diff_url(project, title, diff.from_version, diff.to_version)
        )
        return
    view = viewing_version(state)
    version = view.version if view is not None else None
    webbrowser.open(wiki_service.page_url(project, title, version=version))


_HELP_LINES: list[tuple[str, str]] = [
    (messages.tui_help_section_navigation, ""),
    ("  ↑/k/Ctrl+P", messages.tui_help_move_up),
    ("  ↓/j/Ctrl+N", messages.tui_help_move_down),
    ("  gg / G", messages.tui_help_goto_top_bottom),
    ("  Tab / Shift+Tab", messages.tui_help_switch_tab),
    ("  Ctrl+E / Ctrl+Y", messages.tui_help_preview_scroll_line),
    ("  Ctrl+D / Ctrl+U", messages.tui_help_preview_scroll_half_page),
    (messages.tui_help_section_search, ""),
    ("  /", messages.tui_help_start_search),
    ("  n / N", messages.tui_help_next_prev_match),
    ("  Esc", messages.tui_help_clear_search),
    (messages.tui_help_section_filter, ""),
    ("  p", messages.tui_help_switch_project),
    ("  P", messages.tui_help_switch_profile),
    (messages.tui_help_section_actions, ""),
    ("  Enter", messages.tui_help_wiki_load_text),
    ("  c", messages.tui_help_wiki_create_child),
    ("  u", messages.tui_help_wiki_update_page),
    ("  D", messages.tui_help_wiki_delete_page),
    ("  v", messages.tui_help_wiki_open_web),
    ("  h", messages.tui_help_wiki_versions),
    ("  d", messages.tui_help_wiki_toggle_diff),
    ("  R", messages.tui_help_reload),
    (messages.tui_help_section_other, ""),
    ("  ?", messages.tui_help_show_or_close),
    ("  q / Ctrl+C", messages.tui_help_quit),
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
    on_reload=_on_reload,
    on_resize=noop,
    on_action_key=_on_action_key,
    on_search=_on_search,
    get_cursor_y=lambda state: state.wiki_tab.cursor,
    help_lines=_HELP_LINES,
)
