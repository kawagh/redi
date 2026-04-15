import shutil
from dataclasses import dataclass, field

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from redi.config import default_project_id
from redi.issue import fetch_issues, read_issue


@dataclass
class TuiState:
    page_size: int
    offset: int = 0
    cursor: int = 0
    issues: list[dict] = field(default_factory=list)


def run_issue_tui() -> None:
    state = TuiState(page_size=max(1, shutil.get_terminal_size().lines - 1))
    state.issues = fetch_issues(
        project_id=default_project_id, limit=state.page_size, offset=state.offset
    )
    if not state.issues:
        print("イシューが見つかりません")
        return

    def render_issues():
        result = []
        for i, issue in enumerate(state.issues):
            text = f"#{issue['id']} {issue['subject']}\n"
            result.append(("reverse" if i == state.cursor else "", text))
        return result

    def render_status():
        page = state.offset // state.page_size + 1
        return [
            (
                "reverse",
                f" Page {page} (offset={state.offset})  "
                "↑↓/jk:移動 ←→/hl:ページ Enter:表示 q:終了 ",
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

    @kb.add("enter")
    def _(event):
        event.app.exit(result=str(state.issues[state.cursor]["id"]))

    @kb.add("q")
    @kb.add("escape")
    @kb.add("c-c")
    def _(event):
        event.app.exit(result=None)

    app = Application(
        layout=Layout(
            HSplit(
                [
                    Window(FormattedTextControl(render_issues)),
                    Window(FormattedTextControl(render_status), height=1),
                ]
            )
        ),
        key_bindings=kb,
        full_screen=True,
    )
    result = app.run()
    if result is not None:
        read_issue(result)
