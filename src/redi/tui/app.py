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

from redi.api.issue_status import fetch_issue_statuses
from redi.api.membership import fetch_project_users
from redi.config import default_project_id
from redi.i18n import messages
from redi.tui.issue_tab import (
    ISSUE_TAB,
    fetch_issues_with_filter,
    load_journals,
    reload_with_filter,
)
from redi.tui.state import (
    FIXED_ROWS,
    FilterField,
    FilterModalState,
    IssueFilter,
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
    parts.append(("", messages.tui_tab_switch_hint))
    return parts


def _render_list_current(state: TuiState) -> Renderable:
    return TABS[state.tab].render_list(state)


def _skip_lines(parts: Renderable, n: int) -> Renderable:
    """`parts` の先頭から論理行 (newline 区切り) を `n` 個分捨てて残りを返す。

    prompt_toolkit の `Window` は `wrap_lines=True` 時に `get_vertical_scroll`
    を参照しないため、レンダー結果側で先頭をスライスしてプレビューのスクロール
    を実現する。
    """
    if n <= 0:
        return list(parts)
    result: Renderable = []
    seen = 0
    started = False
    for style, text in parts:
        if started:
            result.append((style, text))
            continue
        nl_in_text = text.count("\n")
        if seen + nl_in_text < n:
            seen += nl_in_text
            continue
        need = n - seen
        idx = -1
        for _ in range(need):
            idx = text.find("\n", idx + 1)
        rest = text[idx + 1 :]
        if rest:
            result.append((style, rest))
        started = True
    return result


def _count_logical_lines(parts: Renderable) -> int:
    if not parts:
        return 0
    return sum(text.count("\n") for _, text in parts) + 1


def _render_preview_current(state: TuiState) -> Renderable:
    parts = TABS[state.tab].render_preview(state)
    if state.preview_scroll <= 0:
        return parts
    return _skip_lines(parts, state.preview_scroll)


def _build_status_choices() -> list[tuple[str | None, str]]:
    """フィルタモーダルのステータス選択肢。先頭の3つは Redmine の特殊指定。"""
    choices: list[tuple[str | None, str]] = [
        (None, messages.tui_filter_status_open_default),
        ("*", messages.tui_filter_status_all),
        ("closed", messages.tui_filter_status_closed_only),
    ]
    for s in fetch_issue_statuses():
        choices.append((str(s["id"]), s.get("name", "")))
    return choices


def _build_assignee_choices(project_id: str | None) -> list[tuple[str | None, str]]:
    """フィルタモーダルの担当者選択肢。先頭は特殊指定 (未設定/me/未割当)。"""
    choices: list[tuple[str | None, str]] = [
        (None, messages.tui_filter_assignee_none),
        ("me", messages.tui_filter_assignee_me),
        ("!*", messages.tui_filter_assignee_unassigned),
    ]
    if project_id:
        for u in fetch_project_users(project_id):
            choices.append((str(u["id"]), u.get("name", "")))
    return choices


def _render_filter_section(
    modal: FilterModalState,
    section: FilterField,
    title: str,
    choices: list[tuple[str | None, str]],
    cursor: int,
    active_id: str | None,
) -> Renderable:
    focused = modal.focus == section
    header_style = "bold fg:ansicyan" if focused else "bold"
    parts: Renderable = [(header_style, f"[{title}]\n")]
    for i, (api_val, label) in enumerate(choices):
        is_cursor = focused and i == cursor
        is_active = api_val == active_id
        cursor_mark = ">" if is_cursor else " "
        active_mark = "*" if is_active else " "
        line_style = "reverse" if is_cursor else ("bold" if is_active else "")
        parts.append((line_style, f" {cursor_mark} {active_mark} {label}\n"))
    return parts


def _render_filter_modal(state: TuiState) -> Renderable:
    f = state.issue_tab.filter
    modal = state.issue_tab.filter_modal
    parts: Renderable = []
    parts.extend(
        _render_filter_section(
            modal,
            "status",
            messages.tui_filter_status,
            modal.status_choices,
            modal.status_cursor,
            f.status_id,
        )
    )
    parts.append(("", "\n"))
    parts.extend(
        _render_filter_section(
            modal,
            "assignee",
            messages.tui_filter_assignee,
            modal.assignee_choices,
            modal.assignee_cursor,
            f.assigned_to_id,
        )
    )
    parts.append(("", messages.tui_filter_hint))
    return parts


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
    initial_offset = position.offset if state.tab == "issues" else 0
    initial_page = fetch_issues_with_filter(state, initial_offset)
    state.issue_tab.offset = initial_offset
    state.issue_tab.issues = initial_page["issues"]
    state.issue_tab.total_count = initial_page.get(
        "total_count", len(state.issue_tab.issues)
    )
    if state.tab == "issues" and not state.issue_tab.issues:
        print(messages.issue_not_found_simple)
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
            and not state.issue_tab.filter_modal.show
        )
    )
    search_mode = Condition(lambda: state.search_mode)
    confirm_delete_mode = Condition(lambda: state.confirm_delete_prompt is not None)
    help_mode = Condition(lambda: state.show_help)
    filter_mode = Condition(lambda: state.issue_tab.filter_modal.show)

    def _clear_temporary_state() -> None:
        state.number_buffer = ""
        state.flash_message = None

    def _reset_preview_scroll() -> None:
        state.preview_scroll = 0

    def _scroll_preview(delta: int) -> None:
        new_scroll = max(0, state.preview_scroll + delta)
        # 最低 1 行は表示が残るように、クランプは「論理行数 - 1」まで。
        # wrap_lines=True で実視覚行は logical を超え得るが、簡易クランプとして許容。
        total = _count_logical_lines(TABS[state.tab].render_preview(state))
        new_scroll = min(new_scroll, max(0, total - 1))
        state.preview_scroll = new_scroll

    @kb.add("tab", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        _reset_preview_scroll()
        tab_keys = list(TABS.keys())
        idx = tab_keys.index(state.tab)
        state.tab = tab_keys[(idx + 1) % len(tab_keys)]
        TABS[state.tab].on_activate(state)

    @kb.add("s-tab", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        _reset_preview_scroll()
        tab_keys = list(TABS.keys())
        idx = tab_keys.index(state.tab)
        state.tab = tab_keys[(idx - 1) % len(tab_keys)]
        TABS[state.tab].on_activate(state)

    @kb.add("up", filter=normal_mode)
    @kb.add("k", filter=normal_mode)
    @kb.add("c-p", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        _reset_preview_scroll()
        TABS[state.tab].on_up(state)

    @kb.add("down", filter=normal_mode)
    @kb.add("j", filter=normal_mode)
    @kb.add("c-n", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        _reset_preview_scroll()
        TABS[state.tab].on_down(state)

    @kb.add("g", "g", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        _reset_preview_scroll()
        TABS[state.tab].on_goto_top(state)

    @kb.add("G", filter=normal_mode)
    def _(event):
        if state.number_buffer:
            try:
                target_id = int(state.number_buffer)
            except ValueError:
                target_id = None
            _clear_temporary_state()
            _reset_preview_scroll()
            if target_id is not None:
                TABS[state.tab].on_jump_to_id(state, target_id)
        else:
            _reset_preview_scroll()
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
        _reset_preview_scroll()
        TABS[state.tab].on_page_forward(state)

    @kb.add("left", filter=normal_mode)
    @kb.add("h", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        _reset_preview_scroll()
        TABS[state.tab].on_page_backward(state)

    @kb.add("c-e", filter=normal_mode)
    def _(event):
        _scroll_preview(1)

    @kb.add("c-y", filter=normal_mode)
    def _(event):
        _scroll_preview(-1)

    @kb.add("c-d", filter=normal_mode)
    def _(event):
        _scroll_preview(max(1, state.page_size // 2))

    @kb.add("c-u", filter=normal_mode)
    def _(event):
        _scroll_preview(-max(1, state.page_size // 2))

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
            _reset_preview_scroll()
            TABS[state.tab].on_search(state, state.search_query, forward=True)
            return
        result = TABS[state.tab].on_action_key(state, "n")
        if result is not None:
            event.app.exit(result=result)

    @kb.add("N", filter=normal_mode)
    def _(event):
        _clear_temporary_state()
        if state.search_query:
            _reset_preview_scroll()
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

    def _open_filter_modal() -> None:
        modal = state.issue_tab.filter_modal
        modal.status_choices = _build_status_choices()
        modal.assignee_choices = _build_assignee_choices(default_project_id)
        modal.status_cursor = 0
        for idx, (api_val, _label) in enumerate(modal.status_choices):
            if api_val == state.issue_tab.filter.status_id:
                modal.status_cursor = idx
                break
        modal.assignee_cursor = 0
        for idx, (api_val, _label) in enumerate(modal.assignee_choices):
            if api_val == state.issue_tab.filter.assigned_to_id:
                modal.assignee_cursor = idx
                break
        modal.focus = "status"
        modal.show = True

    @kb.add("f", filter=normal_mode)
    def _(event):
        if state.tab != "issues":
            return
        _clear_temporary_state()
        _open_filter_modal()

    @kb.add("tab", filter=filter_mode)
    @kb.add("s-tab", filter=filter_mode)
    @kb.add("h", filter=filter_mode)
    @kb.add("l", filter=filter_mode)
    @kb.add("left", filter=filter_mode)
    @kb.add("right", filter=filter_mode)
    def _(event):
        modal = state.issue_tab.filter_modal
        modal.focus = "assignee" if modal.focus == "status" else "status"

    @kb.add("j", filter=filter_mode)
    @kb.add("down", filter=filter_mode)
    def _(event):
        modal = state.issue_tab.filter_modal
        if modal.focus == "status":
            modal.status_cursor = min(
                len(modal.status_choices) - 1, modal.status_cursor + 1
            )
        else:
            modal.assignee_cursor = min(
                len(modal.assignee_choices) - 1, modal.assignee_cursor + 1
            )

    @kb.add("k", filter=filter_mode)
    @kb.add("up", filter=filter_mode)
    def _(event):
        modal = state.issue_tab.filter_modal
        if modal.focus == "status":
            modal.status_cursor = max(0, modal.status_cursor - 1)
        else:
            modal.assignee_cursor = max(0, modal.assignee_cursor - 1)

    @kb.add("enter", filter=filter_mode)
    def _(event):
        modal = state.issue_tab.filter_modal
        if modal.focus == "status":
            if not modal.status_choices:
                return
            api_val, label = modal.status_choices[modal.status_cursor]
            state.issue_tab.filter.status_id = api_val
            state.issue_tab.filter.status_label = label
        else:
            if not modal.assignee_choices:
                return
            api_val, label = modal.assignee_choices[modal.assignee_cursor]
            state.issue_tab.filter.assigned_to_id = api_val
            state.issue_tab.filter.assigned_to_label = label
        _reset_preview_scroll()
        reload_with_filter(state)

    @kb.add("c", filter=filter_mode)
    def _(event):
        state.issue_tab.filter = IssueFilter()
        modal = state.issue_tab.filter_modal
        modal.status_cursor = 0
        modal.assignee_cursor = 0
        _reset_preview_scroll()
        reload_with_filter(state)

    @kb.add("escape", filter=filter_mode)
    @kb.add("f", filter=filter_mode)
    @kb.add("q", filter=filter_mode)
    def _(event):
        state.issue_tab.filter_modal.show = False

    @kb.add("enter", filter=search_mode)
    def _(event):
        if state.search_query:
            _reset_preview_scroll()
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

    preview_window = Window(
        FormattedTextControl(lambda: _render_preview_current(state)),
        wrap_lines=True,
    )

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
                    preview_window,
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
                        title=lambda: messages.tui_help_title.format(
                            label=TABS[state.tab].label
                        ),
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=help_mode,
        ),
    )

    show_filter_cond = Condition(lambda: state.issue_tab.filter_modal.show)
    filter_float = Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        Window(
                            FormattedTextControl(
                                lambda: _render_filter_modal(state), show_cursor=False
                            ),
                            wrap_lines=False,
                        ),
                        title=messages.tui_filter_title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=show_filter_cond,
        ),
    )

    app = Application(
        layout=Layout(
            FloatContainer(content=main_layout, floats=[help_float, filter_float])
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
