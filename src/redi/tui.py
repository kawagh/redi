import shutil
import webbrowser
from dataclasses import dataclass, field
from typing import Literal

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from wcwidth import wcswidth

from redi.config import default_project_id, redmine_url
from redi.issue import fetch_issues


def _pad_display(text: str, width: int) -> str:
    padding = max(0, width - wcswidth(text))
    return text + " " * padding


@dataclass
class TuiState:
    page_size: int
    offset: int = 0
    cursor: int = 0
    issues: list[dict] = field(default_factory=list)


TuiAction = Literal["view", "update", "create"]


@dataclass
class TuiPosition:
    offset: int = 0
    cursor: int = 0


@dataclass
class TuiResult:
    action: TuiAction
    issue_id: str | None
    position: TuiPosition


def run_issue_tui(position: TuiPosition | None = None) -> TuiResult | None:
    if position is None:
        position = TuiPosition()
    state = TuiState(page_size=max(1, shutil.get_terminal_size().lines - 1))
    state.offset = position.offset
    state.issues = fetch_issues(
        project_id=default_project_id, limit=state.page_size, offset=state.offset
    )
    if not state.issues:
        print("イシューが見つかりません")
        return None
    state.cursor = max(0, min(position.cursor, len(state.issues) - 1))

    def render_issues():
        result = []
        for i, issue in enumerate(state.issues):
            text = f"#{issue['id']} {issue['subject']}\n"
            result.append(("reverse" if i == state.cursor else "", text))
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

        return [("", "\n".join(lines))]

    def render_status():
        page = state.offset // state.page_size + 1
        return [
            (
                "reverse",
                f" Page {page} (offset={state.offset})  "
                "↑↓/jk:移動 ←→/hl:ページ Enter:表示 c:作成 u:更新 v:web q:終了 ",
            )
        ]

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _(event):
        state.cursor = max(0, state.cursor - 1)

    @kb.add("down")
    @kb.add("j")
    def _(event):
        state.cursor = min(len(state.issues) - 1, state.cursor + 1)

    @kb.add("right")
    @kb.add("l")
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

    @kb.add("left")
    @kb.add("h")
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

    @kb.add("enter")
    def _(event):
        event.app.exit(result=_exit_with("view"))

    @kb.add("u")
    def _(event):
        event.app.exit(result=_exit_with("update"))

    @kb.add("c")
    def _(event):
        event.app.exit(result=_exit_with("create", issue_id=""))

    @kb.add("v")
    def _(event):
        issue_id = state.issues[state.cursor]["id"]
        webbrowser.open(f"{redmine_url}/issues/{issue_id}")

    @kb.add("q")
    @kb.add("escape")
    @kb.add("c-c")
    def _(event):
        event.app.exit(result=None)

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
    return app.run()
