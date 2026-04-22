from collections.abc import Callable
from dataclasses import dataclass

from redi.tui.state import Renderable, TuiResult, TuiState


@dataclass
class TabView:
    label: str
    render_list: Callable[[TuiState], Renderable]
    render_preview: Callable[[TuiState], Renderable]
    status_hint: Callable[[TuiState], str]
    on_up: Callable[[TuiState], None]
    on_down: Callable[[TuiState], None]
    on_enter: Callable[[TuiState], None]
    on_page_forward: Callable[[TuiState], None]
    on_page_backward: Callable[[TuiState], None]
    on_open_web: Callable[[TuiState], None]
    on_activate: Callable[[TuiState], None]
    on_action_key: Callable[[TuiState, str], TuiResult | None]
    # 一覧内でのカーソル行 (0-indexed)。prompt_toolkit の Window 自動スクロールに使う。
    get_cursor_y: Callable[[TuiState], int]


def noop(state: TuiState) -> None:
    pass
