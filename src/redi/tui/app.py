import shutil
from datetime import datetime
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame

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
from redi.tui.time_entry_tab import (
    TIME_ENTRY_TAB,
    confirm_delete as time_entry_confirm_delete,
    request_delete as time_entry_request_delete,
)
from redi.tui.wiki_tab import WIKI_TAB

TABS: dict[TuiTab, TabView] = {
    "issues": ISSUE_TAB,
    "time_entries": TIME_ENTRY_TAB,
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


def _render_help(state: TuiState) -> Renderable:
    lines = TABS[state.tab].help_lines
    width = max(len(key) for key, _ in lines) + 2
    parts: Renderable = []
    seen_section = False
    for key, desc in lines:
        if not desc:
            if seen_section:
                parts.append(("", "\n"))
            parts.append(("bold", f"{key}\n"))
            seen_section = True
        else:
            parts.append(("bold fg:ansicyan", key.ljust(width)))
            parts.append(("", f"  {desc}\n"))
    return parts


def _render_status(state: TuiState) -> Renderable:
    if state.confirm_delete_prompt is not None:
        return [("reverse", f" {state.confirm_delete_prompt} ")]
    if state.flash_message is not None:
        return [("bold fg:ansiyellow", f" {state.flash_message} ")]
    if state.search_mode:
        return [("reverse", f" /{state.search_query}")]
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
    if state.tab == "time_entries":
        TABS["time_entries"].on_activate(state)
        if last and last.tab == "time_entries":
            max_cursor = max(0, len(state.time_entry_tab.entries) - 1)
            state.time_entry_tab.cursor = min(last.position.cursor, max_cursor)

    kb = KeyBindings()
    normal_mode = Condition(
        lambda: (
            not state.search_mode
            and state.confirm_delete_prompt is None
            and not state.show_help
        )
    )
    search_mode = Condition(lambda: state.search_mode)
    confirm_delete_mode = Condition(lambda: state.confirm_delete_prompt is not None)
    help_mode = Condition(lambda: state.show_help)

    def _clear_temporary_state() -> None:
        state.number_buffer = ""
        state.flash_message = None

    @kb.add("tab", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        tab_keys = list(TABS.keys())
        idx = tab_keys.index(state.tab)
        state.tab = tab_keys[(idx + 1) % len(tab_keys)]
        TABS[state.tab].on_activate(state)

    @kb.add("s-tab", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        tab_keys = list(TABS.keys())
        idx = tab_keys.index(state.tab)
        state.tab = tab_keys[(idx - 1) % len(tab_keys)]
        TABS[state.tab].on_activate(state)

    @kb.add("up", filter=normal_mode)
    @kb.add("k", filter=normal_mode)
    @kb.add("c-p", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        TABS[state.tab].on_up(state)

    @kb.add("down", filter=normal_mode)
    @kb.add("j", filter=normal_mode)
    @kb.add("c-n", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        TABS[state.tab].on_down(state)

    @kb.add("g", "g", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        TABS[state.tab].on_goto_top(state)

    @kb.add("G", filter=normal_mode)
    def _(event):
        if state.number_buffer:
            try:
                target_id = int(state.number_buffer)
            except ValueError:
                target_id = None
            _clear_temporary_state()
            if target_id is not None:
                TABS[state.tab].on_jump_to_id(state, target_id)
        else:
            TABS[state.tab].on_goto_bottom(state)

    for digit in "0123456789":

        @kb.add(digit, filter=normal_mode)
        def _(event, digit=digit):
            # 先頭 0 は無視 (多桁数字の中では許容)。
            if not state.number_buffer and digit == "0":
                return
            state.number_buffer += digit

    @kb.add("right", filter=normal_mode)
    @kb.add("l", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        TABS[state.tab].on_page_forward(state)

    @kb.add("left", filter=normal_mode)
    @kb.add("h", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        TABS[state.tab].on_page_backward(state)

    @kb.add("enter", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        TABS[state.tab].on_enter(state)

    @kb.add("v", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        TABS[state.tab].on_open_web(state)

    @kb.add("V", filter=normal_mode)
    def _(event):
        if state.number_buffer:
            try:
                target_id = int(state.number_buffer)
            except ValueError:
                target_id = None
            _clear_temporary_state()
            if target_id is not None:
                TABS[state.tab].on_open_web_by_id(state, target_id)

    for action_key in ("u", "c", "t"):

        @kb.add(action_key, filter=normal_mode)
        def _(event, action_key=action_key):
            _clear_temporary_state()
            result = TABS[state.tab].on_action_key(state, action_key)
            if result is not None:
                event.app.exit(result=result)

    @kb.add("n", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        if state.search_query:
            TABS[state.tab].on_search(state, state.search_query, forward=True)
            return
        result = TABS[state.tab].on_action_key(state, "n")
        if result is not None:
            event.app.exit(result=result)

    @kb.add("N", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        if state.search_query:
            TABS[state.tab].on_search(state, state.search_query, forward=False)

    @kb.add("/", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        state.search_mode = True
        state.search_query = ""

    @kb.add("D", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        if state.tab != "time_entries":
            return
        prompt = time_entry_request_delete(state)
        if prompt is not None:
            state.confirm_delete_prompt = prompt

    @kb.add("y", filter=confirm_delete_mode)
    @kb.add("Y", filter=confirm_delete_mode)
    def _(event):
        state.confirm_delete_prompt = None
        if state.tab == "time_entries":
            time_entry_confirm_delete(state)

    @kb.add("<any>", filter=confirm_delete_mode)
    def _(event):
        state.confirm_delete_prompt = None

    @kb.add("q", filter=normal_mode)
    @kb.add("escape", filter=normal_mode)
    @kb.add("c-c", filter=normal_mode)
    def _(event):
        event.app.exit(result=None)

    @kb.add("?", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        state.show_help = True

    @kb.add("<any>", filter=help_mode)
    def _(event):
        state.show_help = False

    @kb.add("enter", filter=search_mode)
    def _(event):
        if state.search_query:
            TABS[state.tab].on_search(state, state.search_query)
        state.search_mode = False

    @kb.add("escape", filter=search_mode)
    @kb.add("c-c", filter=search_mode)
    def _(event):
        state.search_mode = False
        state.search_query = ""

    @kb.add("backspace", filter=search_mode)
    def _(event):
        if state.search_query:
            state.search_query = state.search_query[:-1]
        else:
            state.search_mode = False

    @kb.add("<any>", filter=search_mode)
    def _(event):
        data = event.data
        if data and len(data) == 1 and data.isprintable():
            state.search_query += data

    main_layout = HSplit(
        [
            Window(
                FormattedTextControl(lambda: _render_tabs(state), show_cursor=False),
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
                        FormattedTextControl(lambda: _render_preview_current(state)),
                        wrap_lines=True,
                    ),
                ]
            ),
            Window(FormattedTextControl(lambda: _render_status(state)), height=1),
        ]
    )

    # Frame を VSplit で挟んで左右に幅1の空白パディングを置く。
    # Float の真下の行が CJK 文字 (display width=2) で終わると、その2セル目と
    # Frame の左ボーダーが同じ列に重なり、prompt_toolkit のレンダラが wide
    # char の幅ぶんカーソルを進めて Frame ボーダーのセルをスキップしてしまう
    # (= 縁が表示されない)。1セルの空白を挟むとスキップ先がボーダーではなく
    # 空白セルに変わるので、ボーダーは常に描画される。
    help_float = Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        Window(
                            FormattedTextControl(
                                lambda: _render_help(state), show_cursor=False
                            ),
                            wrap_lines=False,
                        ),
                        title=lambda: (
                            f"ヘルプ - {TABS[state.tab].label} タブ "
                            "(任意のキーで閉じる)"
                        ),
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=help_mode,
        ),
    )

    app = Application(
        layout=Layout(FloatContainer(content=main_layout, floats=[help_float])),
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
