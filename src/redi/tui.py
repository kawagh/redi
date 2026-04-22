import shutil
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

import requests
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from wcwidth import wcswidth

from redi.config import default_project_id, redmine_url, wiki_project_id
from redi.api.issue import fetch_issue, fetch_issues
from redi.api.wiki import fetch_wiki, fetch_wikis, flatten_wiki_tree


def dump_rendered_screen(app: Application) -> dict:
    """
    最後にレンダリングした画面 (`_last_screen`) の内容を
    `{"width": int, "height": int, "lines": [str, ...]}` 形式で返す。
    """
    screen = app.renderer._last_screen
    if screen is None:
        return {"width": 0, "height": 0, "lines": []}
    size = app.output.get_size()
    width, height = size.columns, size.rows
    lines = []
    for y in range(height):
        row = screen.data_buffer[y]
        line = "".join(row[x].char for x in range(width)).rstrip()
        lines.append(line)
    return {"width": width, "height": height, "lines": lines}


def _append_screen_yaml(path: Path, dumped: dict, key: str) -> None:
    timestamp = datetime.now().isoformat(timespec="microseconds")
    lines = dumped["lines"]
    indented = "\n".join(f"    {line}" for line in lines) if lines else "    "
    entry = (
        f"- timestamp: {timestamp}\n"
        f"  key: {key}\n"
        f"  width: {dumped['width']}\n"
        f"  height: {dumped['height']}\n"
        f"  screen: |\n{indented}\n"
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)


def _pad_display(text: str, width: int) -> str:
    padding = max(0, width - wcswidth(text))
    return text + " " * padding


def _render_meta_table(meta: list[tuple[str, str]]) -> list[str]:
    """
    `[ラベル] 値` 形式のメタ情報テーブルを整形する。ラベル列はメタの中で
    最大表示幅に揃える。値が空文字列のときは `-` を表示する。
    """
    if not meta:
        return []
    label_width = max(wcswidth(label) for label, _ in meta)
    return [
        f"[{_pad_display(label, label_width)}] {value if value else '-'}"
        for label, value in meta
    ]


TuiAction = Literal["update", "create", "comment"]
TuiTab = Literal["issues", "wiki"]

# 一覧/プレビューの外側にある固定行の合計 (タブバー + 罫線 + ステータスバー)。
# Layout の HSplit に固定行を増減したらここも更新すること。
_FIXED_ROWS = 3


@dataclass
class TuiPosition:
    offset: int = 0
    cursor: int = 0


@dataclass
class TuiResult:
    action: TuiAction
    issue_id: str | None
    position: TuiPosition


@dataclass
class IssueTabState:
    offset: int = 0
    cursor: int = 0
    issues: list[dict] = field(default_factory=list)


@dataclass
class WikiTabState:
    loaded: bool = False
    pages: list[dict] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    cursor: int = 0
    texts: dict[str, str] = field(default_factory=dict)
    error: str | None = None


@dataclass
class TuiState:
    last_result: TuiResult | None = None
    page_size: int = 0
    tab: TuiTab = "issues"
    issue_tab: IssueTabState = field(default_factory=IssueTabState)
    wiki_tab: WikiTabState = field(default_factory=WikiTabState)


# ---- data loaders ---------------------------------------------------------


def _load_journals(issue: dict) -> None:
    fetched = fetch_issue(str(issue["id"]), include="journals")
    issue["journals"] = fetched.get("journals") or []


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


def _exit_result(
    state: TuiState, action: TuiAction, issue_id: str | None = None
) -> TuiResult:
    if issue_id is None and state.issue_tab.issues:
        issue_id = str(state.issue_tab.issues[state.issue_tab.cursor]["id"])
    return TuiResult(
        action=action,
        issue_id=issue_id,
        position=TuiPosition(
            offset=state.issue_tab.offset, cursor=state.issue_tab.cursor
        ),
    )


# ---- per-tab renderers ---------------------------------------------------


def _render_issue_list(state: TuiState) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for i, issue in enumerate(state.issue_tab.issues):
        prefix = "> " if i == state.issue_tab.cursor else "  "
        text = f"{prefix}#{issue['id']} {issue['subject']}\n"
        result.append(("", text))
    return result


def _render_issue_preview(state: TuiState) -> list[tuple[str, str]]:
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
        ("作成", issue.get("created_on") or ""),
        ("更新", issue.get("updated_on") or ""),
    ]
    lines.extend(_render_meta_table(meta))

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


def _render_wiki_list(state: TuiState) -> list[tuple[str, str]]:
    if state.wiki_tab.error:
        return [("", state.wiki_tab.error)]
    if not state.wiki_tab.labels:
        if state.wiki_tab.loaded:
            return [("", "Wikiページが見つかりません")]
        return [("", "(Wikiを読み込み中...)")]
    result: list[tuple[str, str]] = []
    for i, label in enumerate(state.wiki_tab.labels):
        prefix = "> " if i == state.wiki_tab.cursor else "  "
        result.append(("", f"{prefix}{label}\n"))
    return result


def _render_wiki_preview(state: TuiState) -> list[tuple[str, str]]:
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
    lines.extend(_render_meta_table(meta))

    text = state.wiki_tab.texts.get(title)
    lines.append("")
    lines.append("----")
    if text is None:
        lines.append("(Enter で本文をロード)")
    else:
        lines.extend(text.splitlines())
    return [("", "\n".join(lines))]


# ---- per-tab handlers ----------------------------------------------------


def _issue_on_up(state: TuiState) -> None:
    state.issue_tab.cursor = max(0, state.issue_tab.cursor - 1)


def _issue_on_down(state: TuiState) -> None:
    state.issue_tab.cursor = min(
        len(state.issue_tab.issues) - 1, state.issue_tab.cursor + 1
    )


def _issue_on_enter(state: TuiState) -> None:
    if not state.issue_tab.issues:
        return
    issue = state.issue_tab.issues[state.issue_tab.cursor]
    if issue.get("id") is None:
        return
    _load_journals(issue)


def _issue_on_page_forward(state: TuiState) -> None:
    next_issues = fetch_issues(
        project_id=default_project_id,
        limit=state.page_size,
        offset=state.issue_tab.offset + state.page_size,
    )
    if next_issues:
        state.issue_tab.offset += state.page_size
        state.issue_tab.issues = next_issues
        state.issue_tab.cursor = 0


def _issue_on_page_backward(state: TuiState) -> None:
    if state.issue_tab.offset <= 0:
        return
    state.issue_tab.offset = max(0, state.issue_tab.offset - state.page_size)
    state.issue_tab.issues = fetch_issues(
        project_id=default_project_id,
        limit=state.page_size,
        offset=state.issue_tab.offset,
    )
    state.issue_tab.cursor = 0


def _issue_on_open_web(state: TuiState) -> None:
    if not state.issue_tab.issues:
        return
    issue_id = state.issue_tab.issues[state.issue_tab.cursor]["id"]
    webbrowser.open(f"{redmine_url}/issues/{issue_id}")


def _issue_on_action_key(state: TuiState, key: str) -> TuiResult | None:
    if key == "u":
        return _exit_result(state, "update")
    if key == "c":
        return _exit_result(state, "create", issue_id="")
    if key == "n":
        return _exit_result(state, "comment")
    return None


def _issue_status_hint(state: TuiState) -> str:
    page = state.issue_tab.offset // state.page_size + 1
    return (
        f" Page {page} (offset={state.issue_tab.offset})  "
        "↑↓/jk:移動 ←→/hl:ページ Enter:コメント読込 c:作成 u:更新 "
        "n:コメント v:web Tab:タブ切替 q:終了 "
    )


def _wiki_on_up(state: TuiState) -> None:
    state.wiki_tab.cursor = max(0, state.wiki_tab.cursor - 1)


def _wiki_on_down(state: TuiState) -> None:
    if state.wiki_tab.pages:
        state.wiki_tab.cursor = min(
            len(state.wiki_tab.pages) - 1, state.wiki_tab.cursor + 1
        )


def _wiki_on_enter(state: TuiState) -> None:
    if not state.wiki_tab.pages:
        return
    title = state.wiki_tab.pages[state.wiki_tab.cursor].get("title")
    if title:
        _load_wiki_text(state, title)


def _wiki_on_open_web(state: TuiState) -> None:
    if not state.wiki_tab.pages:
        return
    project = _wiki_project()
    if not project:
        return
    title = state.wiki_tab.pages[state.wiki_tab.cursor].get("title")
    if title:
        webbrowser.open(f"{redmine_url}/projects/{project}/wiki/{title}")


def _wiki_status_hint(state: TuiState) -> str:
    return " ↑↓/jk:移動 Enter:本文ロード v:web Tab:タブ切替 q:終了 "


def _noop(state: TuiState) -> None:
    pass


def _no_action(state: TuiState, key: str) -> TuiResult | None:
    return None


# ---- tab registry --------------------------------------------------------


@dataclass
class TabView:
    label: str
    render_list: Callable[[TuiState], list[tuple[str, str]]]
    render_preview: Callable[[TuiState], list[tuple[str, str]]]
    status_hint: Callable[[TuiState], str]
    on_up: Callable[[TuiState], None]
    on_down: Callable[[TuiState], None]
    on_enter: Callable[[TuiState], None]
    on_page_forward: Callable[[TuiState], None]
    on_page_backward: Callable[[TuiState], None]
    on_open_web: Callable[[TuiState], None]
    on_activate: Callable[[TuiState], None]
    on_action_key: Callable[[TuiState, str], TuiResult | None]


ISSUE_TAB = TabView(
    label="イシュー",
    render_list=_render_issue_list,
    render_preview=_render_issue_preview,
    status_hint=_issue_status_hint,
    on_up=_issue_on_up,
    on_down=_issue_on_down,
    on_enter=_issue_on_enter,
    on_page_forward=_issue_on_page_forward,
    on_page_backward=_issue_on_page_backward,
    on_open_web=_issue_on_open_web,
    on_activate=_noop,
    on_action_key=_issue_on_action_key,
)

WIKI_TAB = TabView(
    label="Wiki",
    render_list=_render_wiki_list,
    render_preview=_render_wiki_preview,
    status_hint=_wiki_status_hint,
    on_up=_wiki_on_up,
    on_down=_wiki_on_down,
    on_enter=_wiki_on_enter,
    on_page_forward=_noop,
    on_page_backward=_noop,
    on_open_web=_wiki_on_open_web,
    on_activate=_load_wikis,
    on_action_key=_no_action,
)

TABS: dict[TuiTab, TabView] = {
    "issues": ISSUE_TAB,
    "wiki": WIKI_TAB,
}


# ---- top-level renderers (dispatch through TABS) -------------------------


def _render_tabs(state: TuiState) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    for i, (key, tab) in enumerate(TABS.items()):
        if i > 0:
            parts.append(("", "  "))
        style = "reverse" if state.tab == key else ""
        parts.append((style, f" {tab.label} "))
    parts.append(("", "   (Tab:切替)"))
    return parts


def _render_list_current(state: TuiState) -> list[tuple[str, str]]:
    return TABS[state.tab].render_list(state)


def _render_preview_current(state: TuiState) -> list[tuple[str, str]]:
    return TABS[state.tab].render_preview(state)


def _render_status(state: TuiState) -> list[tuple[str, str]]:
    return [("reverse", TABS[state.tab].status_hint(state))]


# ---- entry point ---------------------------------------------------------


def run_issue_tui(
    state: TuiState | None = None,
    debug_log_path: Path | None = None,
) -> TuiResult | None:
    if state is None:
        state = TuiState()
    last = state.last_result
    position = last.position if last else TuiPosition()
    state.page_size = max(1, shutil.get_terminal_size().lines - _FIXED_ROWS)
    state.issue_tab.offset = position.offset
    state.issue_tab.issues = fetch_issues(
        project_id=default_project_id,
        limit=state.page_size,
        offset=state.issue_tab.offset,
    )
    if not state.issue_tab.issues:
        print("イシューが見つかりません")
        return None
    state.issue_tab.cursor = max(
        0, min(position.cursor, len(state.issue_tab.issues) - 1)
    )
    if last and last.action == "comment" and last.issue_id:
        target_id = int(last.issue_id)
        target = next(
            (i for i in state.issue_tab.issues if i.get("id") == target_id), None
        )
        if target is not None:
            _load_journals(target)

    kb = KeyBindings()

    @kb.add("tab")
    @kb.add("s-tab")
    def _(event):
        state.tab = "wiki" if state.tab == "issues" else "issues"
        TABS[state.tab].on_activate(state)

    @kb.add("up")
    @kb.add("k")
    def _(event):
        TABS[state.tab].on_up(state)

    @kb.add("down")
    @kb.add("j")
    def _(event):
        TABS[state.tab].on_down(state)

    @kb.add("right")
    @kb.add("l")
    def _(event):
        TABS[state.tab].on_page_forward(state)

    @kb.add("left")
    @kb.add("h")
    def _(event):
        TABS[state.tab].on_page_backward(state)

    @kb.add("enter")
    def _(event):
        TABS[state.tab].on_enter(state)

    @kb.add("v")
    def _(event):
        TABS[state.tab].on_open_web(state)

    for action_key in ("u", "c", "n"):

        @kb.add(action_key)
        def _(event, action_key=action_key):
            result = TABS[state.tab].on_action_key(state, action_key)
            if result is not None:
                event.app.exit(result=result)

    @kb.add("q")
    @kb.add("escape")
    @kb.add("c-c")
    def _(event):
        event.app.exit(result=None)

    app = Application(
        layout=Layout(
            HSplit(
                [
                    Window(
                        FormattedTextControl(
                            lambda: _render_tabs(state), show_cursor=False
                        ),
                        height=1,
                    ),
                    Window(height=1, char="─"),
                    VSplit(
                        [
                            Window(
                                FormattedTextControl(
                                    lambda: _render_list_current(state),
                                    show_cursor=False,
                                )
                            ),
                            Window(width=1, char="│"),
                            Window(
                                FormattedTextControl(
                                    lambda: _render_preview_current(state)
                                ),
                                wrap_lines=True,
                            ),
                        ]
                    ),
                    Window(
                        FormattedTextControl(lambda: _render_status(state)), height=1
                    ),
                ]
            )
        ),
        key_bindings=kb,
        full_screen=True,
    )

    if debug_log_path is not None:

        def _on_after_render(sender: Application) -> None:
            seq = sender.key_processor._previous_key_sequence
            key = " ".join(getattr(kp.key, "value", str(kp.key)) for kp in seq)
            _append_screen_yaml(debug_log_path, dump_rendered_screen(sender), key=key)

        app.after_render += _on_after_render

    return app.run()
