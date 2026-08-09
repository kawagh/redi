"""キーバインドのモード判定と、モード間で共有する state 操作。"""

from dataclasses import dataclass

from prompt_toolkit.filters import Condition

from redi.tui.state import Renderable, TuiState
from redi.tui.tabs import TABS


@dataclass(frozen=True)
class Conditions:
    """キーバインドの filter に渡すモード判定。

    modal の表示条件はレイアウトの ConditionalContainer でも使うため、
    `run_issue_tui` で 1 度作って両者で共有する。
    """

    normal: Condition
    search: Condition
    confirm_delete: Condition
    help_modal: Condition
    issue_filter_modal: Condition
    time_entry_filter_modal: Condition
    error_modal: Condition
    project_modal: Condition
    comment_select: Condition


def build_conditions(state: TuiState) -> Conditions:
    return Conditions(
        normal=Condition(
            lambda: (
                not state.search_mode
                and state.confirm_delete_prompt is None
                and not state.show_help
                and not state.issue_tab.filter_modal.show
                and not state.time_entry_tab.filter_modal.show
                and state.error_modal is None
                and not state.issue_tab.comment_select.active
                and not state.project_modal.show
            )
        ),
        search=Condition(lambda: state.search_mode),
        confirm_delete=Condition(lambda: state.confirm_delete_prompt is not None),
        help_modal=Condition(lambda: state.show_help),
        issue_filter_modal=Condition(lambda: state.issue_tab.filter_modal.show),
        time_entry_filter_modal=Condition(
            lambda: state.time_entry_tab.filter_modal.show
        ),
        error_modal=Condition(lambda: state.error_modal is not None),
        project_modal=Condition(lambda: state.project_modal.show),
        comment_select=Condition(
            lambda: (
                state.issue_tab.comment_select.active
                and state.confirm_delete_prompt is None
            )
        ),
    )


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
