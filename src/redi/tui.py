import shutil
import webbrowser
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
from redi.api.wiki import build_children_map, fetch_wiki, fetch_wikis


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


def _load_journals(issue: dict) -> None:
    fetched = fetch_issue(str(issue["id"]), include="journals")
    issue["journals"] = fetched.get("journals") or []


def _flatten_wiki_tree(pages: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Wiki ページをツリー順に並べ替え、ツリー文字付きラベルと対にして返す。
    """
    children_map = build_children_map(pages)
    by_title = {p["title"]: p for p in pages}
    ordered: list[dict] = []
    labels: list[str] = []

    def walk(parent: str | None, prefix: str) -> None:
        children = children_map.get(parent, [])
        for i, title in enumerate(children):
            if title not in by_title:
                continue
            is_last = i == len(children) - 1
            connector = "└── " if is_last else "├── "
            ordered.append(by_title[title])
            labels.append(f"{prefix}{connector}{title}")
            next_prefix = prefix + ("    " if is_last else "│   ")
            walk(title, next_prefix)

    walk(None, "")
    return ordered, labels


TuiAction = Literal["update", "create", "comment"]
TuiTab = Literal["issues", "wiki"]


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


def run_issue_tui(
    state: TuiState | None = None,
    debug_log_path: Path | None = None,
) -> TuiResult | None:
    if state is None:
        state = TuiState()
    last = state.last_result
    position = last.position if last else TuiPosition()
    state.page_size = max(1, shutil.get_terminal_size().lines - 3)
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

    def _wiki_project() -> str | None:
        return wiki_project_id or default_project_id

    def _load_wikis() -> None:
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
        ordered, labels = _flatten_wiki_tree(pages)
        state.wiki_tab.pages = ordered
        state.wiki_tab.labels = labels
        state.wiki_tab.cursor = 0

    def _load_wiki_text(title: str) -> None:
        if title in state.wiki_tab.texts:
            return
        project = _wiki_project()
        if not project:
            return
        try:
            wiki = fetch_wiki(project, title)
        except SystemExit:
            state.wiki_tab.texts[title] = "(読み込みに失敗しました)"
            return
        except requests.exceptions.RequestException as e:
            state.wiki_tab.texts[title] = f"(読み込みに失敗しました: {e})"
            return
        state.wiki_tab.texts[title] = wiki.get("text", "") or ""

    def render_tabs():
        issues_style = "reverse" if state.tab == "issues" else ""
        wiki_style = "reverse" if state.tab == "wiki" else ""
        return [
            (issues_style, " イシュー "),
            ("", "  "),
            (wiki_style, " Wiki "),
            ("", "   (Tab:切替)"),
        ]

    def render_issues():
        result = []
        for i, issue in enumerate(state.issue_tab.issues):
            prefix = "> " if i == state.issue_tab.cursor else "  "
            text = f"{prefix}#{issue['id']} {issue['subject']}\n"
            result.append(("", text))
        return result

    def render_preview():
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
                f"{issue['done_ratio']}%"
                if issue.get("done_ratio") is not None
                else "",
            ),
            ("作成", issue.get("created_on") or ""),
            ("更新", issue.get("updated_on") or ""),
        ]
        label_width = max(wcswidth(label) for label, _ in meta)
        for label, value in meta:
            display_value = value if value else "-"
            lines.append(f"[{_pad_display(label, label_width)}] {display_value}")

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

    def render_wiki_list():
        if state.wiki_tab.error:
            return [("", state.wiki_tab.error)]
        if not state.wiki_tab.labels:
            if state.wiki_tab.loaded:
                return [("", "Wikiページが見つかりません")]
            return [("", "(Wikiを読み込み中...)")]
        result = []
        for i, label in enumerate(state.wiki_tab.labels):
            prefix = "> " if i == state.wiki_tab.cursor else "  "
            result.append(("", f"{prefix}{label}\n"))
        return result

    def render_wiki_preview():
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
        label_width = max(wcswidth(label) for label, _ in meta)
        for label, value in meta:
            display_value = value if value else "-"
            lines.append(f"[{_pad_display(label, label_width)}] {display_value}")

        text = state.wiki_tab.texts.get(title)
        lines.append("")
        lines.append("----")
        if text is None:
            lines.append("(Enter で本文をロード)")
        else:
            lines.extend(text.splitlines())
        return [("", "\n".join(lines))]

    def render_list_current():
        return render_issues() if state.tab == "issues" else render_wiki_list()

    def render_preview_current():
        return render_preview() if state.tab == "issues" else render_wiki_preview()

    def render_status():
        if state.tab == "issues":
            page = state.issue_tab.offset // state.page_size + 1
            return [
                (
                    "reverse",
                    f" Page {page} (offset={state.issue_tab.offset})  "
                    "↑↓/jk:移動 ←→/hl:ページ Enter:コメント読込 c:作成 u:更新 "
                    "n:コメント v:web Tab:タブ切替 q:終了 ",
                )
            ]
        return [
            (
                "reverse",
                " ↑↓/jk:移動 Enter:本文ロード v:web Tab:タブ切替 q:終了 ",
            )
        ]

    kb = KeyBindings()

    @kb.add("tab")
    @kb.add("s-tab")
    def _(event):
        if state.tab == "issues":
            state.tab = "wiki"
            _load_wikis()
        else:
            state.tab = "issues"

    @kb.add("up")
    @kb.add("k")
    def _(event):
        if state.tab == "issues":
            state.issue_tab.cursor = max(0, state.issue_tab.cursor - 1)
        else:
            state.wiki_tab.cursor = max(0, state.wiki_tab.cursor - 1)

    @kb.add("down")
    @kb.add("j")
    def _(event):
        if state.tab == "issues":
            state.issue_tab.cursor = min(
                len(state.issue_tab.issues) - 1, state.issue_tab.cursor + 1
            )
        else:
            if state.wiki_tab.pages:
                state.wiki_tab.cursor = min(
                    len(state.wiki_tab.pages) - 1, state.wiki_tab.cursor + 1
                )

    @kb.add("right")
    @kb.add("l")
    def _(event):
        if state.tab != "issues":
            return
        next_issues = fetch_issues(
            project_id=default_project_id,
            limit=state.page_size,
            offset=state.issue_tab.offset + state.page_size,
        )
        if next_issues:
            state.issue_tab.offset += state.page_size
            state.issue_tab.issues = next_issues
            state.issue_tab.cursor = 0

    @kb.add("left")
    @kb.add("h")
    def _(event):
        if state.tab != "issues":
            return
        if state.issue_tab.offset > 0:
            state.issue_tab.offset = max(0, state.issue_tab.offset - state.page_size)
            state.issue_tab.issues = fetch_issues(
                project_id=default_project_id,
                limit=state.page_size,
                offset=state.issue_tab.offset,
            )
            state.issue_tab.cursor = 0

    def _exit_with(action: TuiAction, issue_id: str | None = None):
        """
        直前の位置を引き継いでTUIのアクションを返す
        """
        if issue_id is None and state.issue_tab.issues:
            issue_id = str(state.issue_tab.issues[state.issue_tab.cursor]["id"])
        return TuiResult(
            action=action,
            issue_id=issue_id,
            position=TuiPosition(
                offset=state.issue_tab.offset, cursor=state.issue_tab.cursor
            ),
        )

    @kb.add("enter")
    def _(event):
        if state.tab == "issues":
            if not state.issue_tab.issues:
                return
            issue = state.issue_tab.issues[state.issue_tab.cursor]
            if issue.get("id") is None:
                return
            _load_journals(issue)
        else:
            if not state.wiki_tab.pages:
                return
            title = state.wiki_tab.pages[state.wiki_tab.cursor].get("title")
            if title:
                _load_wiki_text(title)

    @kb.add("u")
    def _(event):
        if state.tab != "issues":
            return
        event.app.exit(result=_exit_with("update"))

    @kb.add("c")
    def _(event):
        if state.tab != "issues":
            return
        event.app.exit(result=_exit_with("create", issue_id=""))

    # n is first letter of note
    @kb.add("n")
    def _(event):
        if state.tab != "issues":
            return
        event.app.exit(result=_exit_with("comment"))

    @kb.add("v")
    def _(event):
        if state.tab == "issues":
            issue_id = state.issue_tab.issues[state.issue_tab.cursor]["id"]
            webbrowser.open(f"{redmine_url}/issues/{issue_id}")
        else:
            if not state.wiki_tab.pages:
                return
            project = _wiki_project()
            if not project:
                return
            title = state.wiki_tab.pages[state.wiki_tab.cursor].get("title")
            if title:
                webbrowser.open(f"{redmine_url}/projects/{project}/wiki/{title}")

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
                        FormattedTextControl(render_tabs, show_cursor=False),
                        height=1,
                    ),
                    Window(height=1, char="─"),
                    VSplit(
                        [
                            Window(
                                FormattedTextControl(
                                    render_list_current, show_cursor=False
                                )
                            ),
                            Window(width=1, char="│"),
                            Window(
                                FormattedTextControl(render_preview_current),
                                wrap_lines=True,
                            ),
                        ]
                    ),
                    Window(FormattedTextControl(render_status), height=1),
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
