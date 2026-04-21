import shutil
import webbrowser
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

from prompt_toolkit import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from wcwidth import wcswidth

from redi.config import default_project_id, redmine_url
from redi.api.issue import fetch_issue, fetch_issues


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


def _highlight_segments(
    text: str, query: str, base_style: str = ""
) -> list[tuple[str, str]]:
    if not query:
        return [(base_style, text)]
    q = query.lower()
    lower = text.lower()
    segments: list[tuple[str, str]] = []
    i = 0
    while i < len(text):
        pos = lower.find(q, i)
        if pos == -1:
            segments.append((base_style, text[i:]))
            break
        if pos > i:
            segments.append((base_style, text[i:pos]))
        segments.append(("reverse", text[pos : pos + len(q)]))
        i = pos + len(q)
    return segments


def _load_journals(issue: dict) -> None:
    fetched = fetch_issue(str(issue["id"]), include="journals")
    issue["journals"] = fetched.get("journals") or []


TuiAction = Literal["update", "create", "comment"]


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
class TuiState:
    last_result: TuiResult | None = None
    page_size: int = 0
    offset: int = 0
    cursor: int = 0
    issues: list[dict] = field(default_factory=list)
    search_mode: bool = False
    search_query: str = ""


def run_issue_tui(
    state: TuiState | None = None,
    debug_log_path: Path | None = None,
) -> TuiResult | None:
    if state is None:
        state = TuiState()
    last = state.last_result
    position = last.position if last else TuiPosition()
    state.page_size = max(1, shutil.get_terminal_size().lines - 1)
    state.offset = position.offset
    state.issues = fetch_issues(
        project_id=default_project_id, limit=state.page_size, offset=state.offset
    )
    if not state.issues:
        print("イシューが見つかりません")
        return None
    state.cursor = max(0, min(position.cursor, len(state.issues) - 1))
    if last and last.action == "comment" and last.issue_id:
        target_id = int(last.issue_id)
        target = next((i for i in state.issues if i.get("id") == target_id), None)
        if target is not None:
            _load_journals(target)

    def render_issues():
        def named(issue: dict, field: str) -> str:
            value = issue.get(field)
            if isinstance(value, dict):
                return value.get("name", "") or ""
            return ""

        id_width = max(
            (wcswidth(f"#{issue['id']}") for issue in state.issues), default=0
        )
        status_width = max(
            (wcswidth(named(issue, "status")) for issue in state.issues), default=0
        )
        assignee_width = max(
            (wcswidth(named(issue, "assigned_to")) for issue in state.issues),
            default=0,
        )

        query = state.search_query if state.search_mode else ""

        result = []
        for i, issue in enumerate(state.issues):
            cursor_mark = "> " if i == state.cursor else "  "
            id_text = _pad_display(f"#{issue['id']}", id_width)
            status_text = _pad_display(named(issue, "status"), status_width)
            assignee_text = _pad_display(named(issue, "assigned_to"), assignee_width)
            text = (
                f"{cursor_mark}{id_text} {status_text} {assignee_text} "
                f"{issue['subject']}\n"
            )
            result.extend(_highlight_segments(text, query))
        return result

    def render_preview():
        if not state.issues:
            return []
        issue = state.issues[state.cursor]
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

    def render_status():
        page = state.offset // state.page_size + 1
        if state.search_mode:
            return [("reverse", f" Page {page}  /{state.search_query} ")]
        return [
            (
                "reverse",
                f" Page {page} (offset={state.offset})  "
                "↑↓/jk:移動 ←→/hl:ページ Enter:コメント読込 c:作成 u:更新 n:コメント v:web /:検索 q:終了 ",
            )
        ]

    def _find_match() -> None:
        if not state.search_query:
            return
        q = state.search_query.lower()

        def _named(issue: dict, name: str) -> str:
            value = issue.get(name)
            if isinstance(value, dict):
                return value.get("name", "") or ""
            return ""

        for i, issue in enumerate(state.issues):
            haystack = " ".join(
                [
                    f"#{issue.get('id', '')}",
                    str(issue.get("subject") or ""),
                    _named(issue, "status"),
                    _named(issue, "assigned_to"),
                ]
            ).lower()
            if q in haystack:
                state.cursor = i
                return

    kb = KeyBindings()

    is_searching = Condition(lambda: state.search_mode)
    not_searching = Condition(lambda: not state.search_mode)

    @kb.add("up", filter=not_searching)
    @kb.add("k", filter=not_searching)
    def _(event):
        state.cursor = max(0, state.cursor - 1)

    @kb.add("down", filter=not_searching)
    @kb.add("j", filter=not_searching)
    def _(event):
        state.cursor = min(len(state.issues) - 1, state.cursor + 1)

    @kb.add("right", filter=not_searching)
    @kb.add("l", filter=not_searching)
    def _(event):
        next_issues = fetch_issues(
            project_id=default_project_id,
            limit=state.page_size,
            offset=state.offset + state.page_size,
        )
        if next_issues:
            state.offset += state.page_size
            state.issues = next_issues
            state.cursor = 0

    @kb.add("left", filter=not_searching)
    @kb.add("h", filter=not_searching)
    def _(event):
        if state.offset > 0:
            state.offset = max(0, state.offset - state.page_size)
            state.issues = fetch_issues(
                project_id=default_project_id,
                limit=state.page_size,
                offset=state.offset,
            )
            state.cursor = 0

    def _exit_with(action: TuiAction, issue_id: str | None = None):
        """
        直前の位置を引き継いでTUIのアクションを返す
        """
        if issue_id is None and state.issues:
            issue_id = str(state.issues[state.cursor]["id"])
        return TuiResult(
            action=action,
            issue_id=issue_id,
            position=TuiPosition(offset=state.offset, cursor=state.cursor),
        )

    @kb.add("enter", filter=not_searching)
    def _(event):
        if not state.issues:
            return
        issue = state.issues[state.cursor]
        if issue.get("id") is None:
            return
        _load_journals(issue)

    @kb.add("u", filter=not_searching)
    def _(event):
        event.app.exit(result=_exit_with("update"))

    @kb.add("c", filter=not_searching)
    def _(event):
        event.app.exit(result=_exit_with("create", issue_id=""))

    # n is first letter of note
    @kb.add("n", filter=not_searching)
    def _(event):
        event.app.exit(result=_exit_with("comment"))

    @kb.add("v", filter=not_searching)
    def _(event):
        issue_id = state.issues[state.cursor]["id"]
        webbrowser.open(f"{redmine_url}/issues/{issue_id}")

    @kb.add("q", filter=not_searching)
    @kb.add("escape", filter=not_searching)
    @kb.add("c-c")
    def _(event):
        event.app.exit(result=None)

    @kb.add("/", filter=not_searching)
    def _(event):
        state.search_mode = True
        state.search_query = ""

    @kb.add("enter", filter=is_searching)
    def _(event):
        state.search_mode = False

    @kb.add("escape", filter=is_searching)
    def _(event):
        state.search_mode = False
        state.search_query = ""

    @kb.add("backspace", filter=is_searching)
    def _(event):
        state.search_query = state.search_query[:-1]
        _find_match()

    @kb.add("<any>", filter=is_searching)
    def _(event):
        data = event.data
        if data and len(data) == 1 and data.isprintable():
            state.search_query += data
            _find_match()

    app = Application(
        layout=Layout(
            HSplit(
                [
                    VSplit(
                        [
                            Window(FormattedTextControl(render_issues)),
                            Window(width=1, char="│"),
                            Window(FormattedTextControl(render_preview)),
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
