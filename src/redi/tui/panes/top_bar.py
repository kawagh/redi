"""画面上端のバー。タブ・接続中のプロファイル・プロジェクトを 1 行に並べる。

タブのラベルのクリックはラベルごとに対象が違うので、矩形全体を受ける
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
from redi.tui.keybindings.keybinding_actions import activate_tab
from redi.tui.state import TuiState, TuiTab
from redi.tui.tabs import TABS

# タブ行のラベルに付けるマウスハンドラ。タブのキーからハンドラを引く。
# ハンドラの戻り値は None か NotImplemented。prompt_toolkit はこれを object と
# 注釈しており、実行時に使える型別名が無いので同じ書き方にする。
TabMouseHandler = Callable[[TuiTab], Callable[[MouseEvent], object]]


def render_top_bar(
    state: TuiState, on_click: TabMouseHandler | None = None
) -> StyleAndTextTuples:
    """上端のバーを描画する。

    `on_click` を渡すと各タブのラベルにマウスハンドラを付ける。
    """
    parts: StyleAndTextTuples = []
    for i, (key, tab) in enumerate(TABS.items()):
        if i > 0:
            parts.append(("", "  "))
        style = "reverse" if state.tab == key else ""
        label = f" {tab.label} "
        if on_click is None:
            parts.append((style, label))
        else:
            parts.append((style, label, on_click(key)))
    parts.append(("", messages.tui_tab_switch_hint))
    if config.current_profile:
        parts.append(
            (
                "bold fg:ansimagenta",
                messages.tui_current_profile.format(name=config.current_profile),
            )
        )
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


def build_top_bar_window(state: TuiState, conditions: Conditions) -> Window:
    """上端のバーの Window。タブのラベルにクリックハンドラを付けて描画する。"""
    on_click = build_tab_click_handler(state, conditions)
    return Window(
        FormattedTextControl(
            lambda: render_top_bar(state, on_click=on_click),
            show_cursor=False,
        ),
        height=1,
    )
