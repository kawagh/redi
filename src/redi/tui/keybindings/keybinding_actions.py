"""キーバインドから呼ぶ state 操作。"""

from redi.tui.state import Renderable, TuiState
from redi.tui.tabs import TABS


def clear_temporary_state(state: TuiState) -> None:
    state.number_buffer = ""
    state.flash_message = None


def reset_preview_scroll(state: TuiState) -> None:
    state.preview_scroll = 0


def _count_logical_lines(parts: Renderable) -> int:
    if not parts:
        return 0
    return sum(text.count("\n") for _, text in parts) + 1


def scroll_preview(state: TuiState, delta: int) -> None:
    new_scroll = max(0, state.preview_scroll + delta)
    # 最低 1 行は表示が残るように、クランプは「論理行数 - 1」まで。
    # wrap_lines=True で実視覚行は logical を超え得るが、簡易クランプとして許容。
    total = _count_logical_lines(TABS[state.tab].render_preview(state))
    new_scroll = min(new_scroll, max(0, total - 1))
    state.preview_scroll = new_scroll
