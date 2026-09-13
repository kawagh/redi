"""画面上端のバー。タブ・接続中のプロファイル・プロジェクトを 1 行に並べる。

ラベルのクリックはラベルごとに対象が違うので、矩形全体を受ける
`PaneControl` ではなく、描画フラグメントに付けるハンドラで受ける
(prompt_toolkit はフラグメントの 3 要素目をクリック時に呼ぶ)。
"""

from collections.abc import Callable

from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

from redi import config
from redi.i18n import messages
from redi.tui.conditions import Conditions
from redi.tui.keybindings.keybinding_actions import (
    activate_tab,
    clear_temporary_state,
)
from redi.tui.profile_dialog import open_profile_dialog
from redi.tui.project_dialog import open_project_dialog
from redi.tui.state import TuiState, TuiTab
from redi.tui.tabs import TABS

# ラベルに付けるマウスハンドラ。
# ハンドラの戻り値は None か NotImplemented。prompt_toolkit はこれを object と
# 注釈しており、実行時に使える型別名が無いので同じ書き方にする。
LabelMouseHandler = Callable[[MouseEvent], object]
# タブのラベルに付けるマウスハンドラ。タブのキーからハンドラを引く。
TabMouseHandler = Callable[[TuiTab], LabelMouseHandler]


def _with_handler(
    style: str, text: str, handler: LabelMouseHandler | None
) -> tuple[str, str] | tuple[str, str, LabelMouseHandler]:
    if handler is None:
        return (style, text)
    return (style, text, handler)


def render_top_bar(
    state: TuiState,
    on_click: TabMouseHandler | None = None,
    on_profile_click: LabelMouseHandler | None = None,
    on_project_click: LabelMouseHandler | None = None,
) -> StyleAndTextTuples:
    """上端のバーを描画する。

    `on_click` を渡すと各タブのラベルに、`on_profile_click` / `on_project_click` を
    渡すとプロファイル / プロジェクトのラベルにマウスハンドラを付ける。
    """
    parts: StyleAndTextTuples = []
    for i, (key, tab) in enumerate(TABS.items()):
        if i > 0:
            parts.append(("", "  "))
        style = "reverse" if state.tab == key else ""
        label = f" {tab.label} "
        handler = None if on_click is None else on_click(key)
        parts.append(_with_handler(style, label, handler))
    parts.append(("", messages.tui_tab_switch_hint))
    if config.current_profile:
        parts.append(
            _with_handler(
                "bold fg:ansimagenta",
                messages.tui_current_profile.format(name=config.current_profile),
                on_profile_click,
            )
        )
    # 未切替時は名前解決の API を呼ばず config の設定値 (id/identifier) を出す。
    project = state.project_label or state.effective_project_id()
    if project:
        parts.append(
            _with_handler(
                "bold fg:ansicyan",
                messages.tui_current_project.format(name=project),
                on_project_click,
            )
        )
    return parts


def build_tab_click_handler(state: TuiState, conditions: Conditions) -> TabMouseHandler:
    """タブ行のラベルのクリックを Tab キーと同じタブ切り替えに変換する。

    クリックは MOUSE_UP で受ける (prompt_toolkit の Button と同じ流儀)。
    通常モードだけで効き、今のタブをクリックしても再読込はしない。
    """

    def for_tab(tab: TuiTab) -> Callable[[MouseEvent], object]:
        def on_mouse(mouse_event: MouseEvent) -> object:
            if mouse_event.event_type != MouseEventType.MOUSE_UP:
                return NotImplemented
            if not conditions.normal() or state.tab == tab:
                return NotImplemented
            activate_tab(state, tab)
            return None

        return on_mouse

    return for_tab


def _build_dialog_click_handler(
    state: TuiState, conditions: Conditions, open_dialog: Callable[[TuiState], None]
) -> LabelMouseHandler:
    """ラベルのクリックを、ダイアログを開くキーと同じ操作に変換する。

    クリックは MOUSE_UP で受け、通常モードだけで効く。
    """

    def on_mouse(mouse_event: MouseEvent) -> object:
        if mouse_event.event_type != MouseEventType.MOUSE_UP:
            return NotImplemented
        if not conditions.normal():
            return NotImplemented
        clear_temporary_state(state)
        open_dialog(state)
        return None

    return on_mouse


def build_profile_click_handler(
    state: TuiState, conditions: Conditions
) -> LabelMouseHandler:
    """プロファイル名のクリックを P と同じプロファイル切替ダイアログの表示にする。"""
    return _build_dialog_click_handler(state, conditions, open_profile_dialog)


def build_project_click_handler(
    state: TuiState, conditions: Conditions
) -> LabelMouseHandler:
    """プロジェクト名のクリックを p と同じプロジェクト切替ダイアログの表示にする。"""
    return _build_dialog_click_handler(state, conditions, open_project_dialog)


def build_top_bar_window(state: TuiState, conditions: Conditions) -> Window:
    """上端のバーの Window。各ラベルにクリックハンドラを付けて描画する。"""
    on_click = build_tab_click_handler(state, conditions)
    on_profile_click = build_profile_click_handler(state, conditions)
    on_project_click = build_project_click_handler(state, conditions)
    return Window(
        FormattedTextControl(
            lambda: render_top_bar(
                state,
                on_click=on_click,
                on_profile_click=on_profile_click,
                on_project_click=on_project_click,
            ),
            show_cursor=False,
        ),
        height=1,
    )
