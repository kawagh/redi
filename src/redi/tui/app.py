import shutil
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.data_structures import Point
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
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.widgets import Frame

from redi.api.me import fetch_my_user_id
from redi.i18n import messages
from redi.tui.issue.filter_modal import build_filter_float
from redi.tui.issue.issue_tab import fetch_issues_with_filter, load_journals
from redi.tui.keys import modal, mode, normal
from redi.tui.keys.shared import build_conditions
from redi.tui.project_modal import build_project_float
from redi.tui.state import (
    FIXED_ROWS,
    Renderable,
    TuiPosition,
    TuiResult,
    TuiState,
)
from redi.tui.tabs import TABS
from redi.tui.time_entry.filter_modal import (
    build_filter_float as build_time_entry_filter_float,
)


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
    # 未切替時は名前解決の API を呼ばず config の設定値 (id/identifier) を出す。
    project = state.project_label or state.effective_project_id()
    if project:
        parts.append(
            (
                "bold fg:ansicyan",
                messages.tui_current_project.format(name=project),
            )
        )
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


def _render_preview_current(state: TuiState) -> Renderable:
    parts = TABS[state.tab].render_preview(state)
    if state.preview_scroll <= 0:
        return parts
    return _skip_lines(parts, state.preview_scroll)


def _help_version_label() -> str:
    return f"redi v{version('redtile')}"


def _render_help(state: TuiState) -> Renderable:
    lines = TABS[state.tab].help_lines
    width = max(len(key) for key, _ in lines) + 2
    parts: Renderable = []
    seen_section = False
    # バージョン行を右下に寄せるため、本文の最大表示幅 (CJK は2セル) を測る
    body_width = 0
    for key, desc in lines:
        if not desc:
            if seen_section:
                parts.append(("", "\n"))
            parts.append(("bold", f"{key}\n"))
            seen_section = True
            body_width = max(body_width, get_cwidth(key))
        else:
            parts.append(("bold fg:ansicyan", key.ljust(width)))
            parts.append(("", f"  {desc}\n"))
            body_width = max(body_width, width + 2 + get_cwidth(desc))
    label = _help_version_label()
    padding = max(0, body_width - get_cwidth(label))
    parts.append(("", "\n"))
    parts.append(("fg:ansiwhite", f"{' ' * padding}{label}"))
    return parts


def _render_error_modal(state: TuiState) -> Renderable:
    body = state.error_modal or ""
    return [("fg:ansired", body)]


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
    if state.me_id is None:
        state.me_id = fetch_my_user_id()
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
    if state.issue_tab.issues:
        state.issue_tab.cursor = max(
            0, min(position.cursor, len(state.issue_tab.issues) - 1)
        )
    # journalの更新
    if (
        last
        and last.action in ("comment", "edit_comment", "delete_comment")
        and last.issue_id
    ):
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
        if last and last.tab == "time_entries":
            state.time_entry_tab.offset = last.position.offset
        TABS["time_entries"].on_activate(state)
        if last and last.tab == "time_entries":
            max_cursor = max(0, len(state.time_entry_tab.entries) - 1)
            state.time_entry_tab.cursor = min(last.position.cursor, max_cursor)

    conditions = build_conditions(state)
    kb = KeyBindings()
    normal.register(kb, state, conditions)
    modal.register(kb, state, conditions)
    mode.register(kb, state, conditions)

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
            filter=conditions.help_modal,
        ),
    )

    filter_float = build_filter_float(state, conditions.issue_filter_modal)

    time_entry_filter_float = build_time_entry_filter_float(
        state, conditions.time_entry_filter_modal
    )

    project_float = build_project_float(state, conditions.project_modal)

    error_float = Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        Window(
                            FormattedTextControl(
                                lambda: _render_error_modal(state), show_cursor=False
                            ),
                            wrap_lines=True,
                        ),
                        title=lambda: messages.tui_error_modal_title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=conditions.error_modal,
        ),
    )

    app = Application(
        layout=Layout(
            FloatContainer(
                content=main_layout,
                floats=[
                    help_float,
                    filter_float,
                    time_entry_filter_float,
                    project_float,
                    error_float,
                ],
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
