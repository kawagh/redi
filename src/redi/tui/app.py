import shutil
from datetime import datetime
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.data_structures import Point
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from redi.api.issue import fetch_issues
from redi.config import default_project_id
from redi.tui.issue_tab import ISSUE_TAB, load_journals
from redi.tui.state import (
    FIXED_ROWS,
    Renderable,
    TuiPosition,
    TuiResult,
    TuiState,
    TuiTab,
)
from redi.tui.tab import TabView
from redi.tui.wiki_tab import WIKI_TAB

TABS: dict[TuiTab, TabView] = {
    "issues": ISSUE_TAB,
    "wiki": WIKI_TAB,
}


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


def _render_tabs(state: TuiState) -> Renderable:
    parts: Renderable = []
    for i, (key, tab) in enumerate(TABS.items()):
        if i > 0:
            parts.append(("", "  "))
        style = "reverse" if state.tab == key else ""
        parts.append((style, f" {tab.label} "))
    parts.append(("", "   (Tab:切替)"))
    return parts


def _render_list_current(state: TuiState) -> Renderable:
    return TABS[state.tab].render_list(state)


def _render_preview_current(state: TuiState) -> Renderable:
    return TABS[state.tab].render_preview(state)


def _render_status(state: TuiState) -> Renderable:
    hint = TABS[state.tab].status_hint(state)
    if state.number_buffer:
        hint = f" [{state.number_buffer}]" + hint
    return [("reverse", hint)]


def run_issue_tui(
    state: TuiState | None = None,
    debug_log_path: Path | None = None,
) -> TuiResult | None:
    if state is None:
        state = TuiState()
    last = state.last_result
    if last:
        state.tab = last.tab
    position = last.position if last else TuiPosition()
    state.page_size = max(1, shutil.get_terminal_size().lines - FIXED_ROWS)
    state.issue_tab.offset = position.offset if state.tab == "issues" else 0
    state.issue_tab.issues = fetch_issues(
        project_id=default_project_id,
        limit=state.page_size,
        offset=state.issue_tab.offset,
    )
    if state.tab == "issues" and not state.issue_tab.issues:
        print("イシューが見つかりません")
        return None
    if state.issue_tab.issues:
        state.issue_tab.cursor = max(
            0, min(position.cursor, len(state.issue_tab.issues) - 1)
        )
    if last and last.action == "comment" and last.issue_id:
        target_id = int(last.issue_id)
        target = next(
            (i for i in state.issue_tab.issues if i.get("id") == target_id), None
        )
        if target is not None:
            load_journals(target)
    if state.tab == "wiki":
        TABS["wiki"].on_activate(state)
        if last and last.tab == "wiki" and last.wiki_title:
            titles = [p.get("title") for p in state.wiki_tab.pages]
            if last.wiki_title in titles:
                state.wiki_tab.cursor = titles.index(last.wiki_title)

    kb = KeyBindings()

    def _clear_number_buffer() -> None:
        state.number_buffer = ""

    @kb.add("tab")
    @kb.add("s-tab")
    def _(event):
        _clear_number_buffer()
        state.tab = "wiki" if state.tab == "issues" else "issues"
        TABS[state.tab].on_activate(state)

    @kb.add("up")
    @kb.add("k")
    @kb.add("c-p")
    def _(event):
        _clear_number_buffer()
        TABS[state.tab].on_up(state)

    @kb.add("down")
    @kb.add("j")
    @kb.add("c-n")
    def _(event):
        _clear_number_buffer()
        TABS[state.tab].on_down(state)

    @kb.add("g", "g")
    def _(event):
        _clear_number_buffer()
        TABS[state.tab].on_goto_top(state)

    @kb.add("G")
    def _(event):
        if state.number_buffer:
            try:
                target_id = int(state.number_buffer)
            except ValueError:
                target_id = None
            _clear_number_buffer()
            if target_id is not None:
                TABS[state.tab].on_jump_to_id(state, target_id)
        else:
            TABS[state.tab].on_goto_bottom(state)

    for digit in "0123456789":

        @kb.add(digit)
        def _(event, digit=digit):
            # 先頭 0 は無視 (多桁数字の中では許容)。
            if not state.number_buffer and digit == "0":
                return
            state.number_buffer += digit

    @kb.add("right")
    @kb.add("l")
    def _(event):
        _clear_number_buffer()
        TABS[state.tab].on_page_forward(state)

    @kb.add("left")
    @kb.add("h")
    def _(event):
        _clear_number_buffer()
        TABS[state.tab].on_page_backward(state)

    @kb.add("enter")
    def _(event):
        _clear_number_buffer()
        TABS[state.tab].on_enter(state)

    @kb.add("v")
    def _(event):
        _clear_number_buffer()
        TABS[state.tab].on_open_web(state)

    for action_key in ("u", "c", "n"):

        @kb.add(action_key)
        def _(event, action_key=action_key):
            _clear_number_buffer()
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
                                    get_cursor_position=lambda: Point(
                                        0, TABS[state.tab].get_cursor_y(state)
                                    ),
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
