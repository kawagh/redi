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


def noop(state: TuiState) -> None:
    pass


def no_action(state: TuiState, key: str) -> TuiResult | None:
    return None
