from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from redi.config import default_project_id
from redi.issue import fetch_issues, read_issue


def run_issue_tui() -> None:
    page_size = 20
    offset = 0
    cursor = 0
    issues = fetch_issues(project_id=default_project_id, limit=page_size, offset=offset)
    if not issues:
        print("イシューが見つかりません")
        return

    def render_issues():
        result = []
        for i, issue in enumerate(issues):
            text = f"#{issue['id']} {issue['subject']}\n"
            result.append(("reverse" if i == cursor else "", text))
        return result

    def render_status():
        page = offset // page_size + 1
        return [
            (
                "reverse",
                f" Page {page} (offset={offset})  "
                "↑↓/jk:移動 ←→/hl:ページ Enter:表示 q:終了 ",
            )
        ]

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _(event):
        nonlocal cursor
        cursor = max(0, cursor - 1)

    @kb.add("down")
    @kb.add("j")
    def _(event):
        nonlocal cursor
        cursor = min(len(issues) - 1, cursor + 1)

    @kb.add("right")
    @kb.add("l")
    def _(event):
        nonlocal offset, cursor, issues
        next_issues = fetch_issues(
            project_id=default_project_id,
            limit=page_size,
            offset=offset + page_size,
        )
        if next_issues:
            offset += page_size
            issues = next_issues
            cursor = 0

    @kb.add("left")
    @kb.add("h")
    def _(event):
        nonlocal offset, cursor, issues
        if offset > 0:
            offset = max(0, offset - page_size)
            issues = fetch_issues(
                project_id=default_project_id, limit=page_size, offset=offset
            )
            cursor = 0

    @kb.add("enter")
    def _(event):
        event.app.exit(result=str(issues[cursor]["id"]))

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
