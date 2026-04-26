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
    on_goto_top: Callable[[TuiState], None]
    on_goto_bottom: Callable[[TuiState], None]
    on_jump_to_id: Callable[[TuiState, int], None]
    on_enter: Callable[[TuiState], None]
    on_page_forward: Callable[[TuiState], None]
    on_page_backward: Callable[[TuiState], None]
    on_open_web: Callable[[TuiState], None]
    on_open_web_by_id: Callable[[TuiState, int], None]
    on_activate: Callable[[TuiState], None]
    on_action_key: Callable[[TuiState, str], TuiResult | None]
    on_search: Callable[..., None]
    # 一覧内でのカーソル行 (0-indexed)。prompt_toolkit の Window 自動スクロールに使う。
    get_cursor_y: Callable[[TuiState], int]
    # ? で開くヘルプの行データ。`(キー, 説明)` の組のリストで、説明が空の要素は
    # セクション見出しとして描画される。タブごとに利用可能なキーが異なるため
    # 各タブが自前で定義する。
    help_lines: list[tuple[str, str]]


def noop(state: TuiState) -> None:
    pass


def noop_jump(state: TuiState, target_id: int) -> None:
    pass
