"""画面パーツ (タブバー / 一覧 / プレビュー / ヘルプ / ステータスバー) の描画。

一覧とプレビューの本文はタブ側が組み立てる。ここが持つのはタブに依らず画面へ
常に出るものと、ヘルプ・エラー modal の本文。
"""

from importlib.metadata import version

from prompt_toolkit.utils import get_cwidth

from redi.i18n import messages
from redi.tui.state import Renderable, TuiState
from redi.tui.tabs import TABS


def render_tabs(state: TuiState) -> Renderable:
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


def render_list_current(state: TuiState) -> Renderable:
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


def render_preview_current(state: TuiState) -> Renderable:
    parts = TABS[state.tab].render_preview(state)
    if state.preview_scroll <= 0:
        return parts
    return _skip_lines(parts, state.preview_scroll)


def help_version_label() -> str:
    return f"redi v{version('redtile')}"


def render_help(state: TuiState) -> Renderable:
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
    label = help_version_label()
    padding = max(0, body_width - get_cwidth(label))
    parts.append(("", "\n"))
    parts.append(("fg:ansiwhite", f"{' ' * padding}{label}"))
    return parts


def render_error_modal(state: TuiState) -> Renderable:
    body = state.error_modal or ""
    return [("fg:ansired", body)]


def render_status(state: TuiState) -> Renderable:
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
