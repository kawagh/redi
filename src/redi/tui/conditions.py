"""表示・入力モードの判定。

キーバインドの filter とレイアウトの ConditionalContainer の両方が同じ条件を
見るため、`run_issue_tui` で 1 度作って共有する。
"""

from dataclasses import dataclass

from prompt_toolkit.filters import Condition

from redi.tui.state import TuiState


@dataclass(frozen=True)
class Conditions:
    normal: Condition
    search: Condition
    confirm_delete: Condition
    help_modal: Condition
    issue_filter_modal: Condition
    time_entry_filter_modal: Condition
    error_modal: Condition
    project_modal: Condition
    profile_modal: Condition
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
                and not state.profile_modal.show
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
        profile_modal=Condition(lambda: state.profile_modal.show),
        comment_select=Condition(
            lambda: (
                state.issue_tab.comment_select.active
                and state.confirm_delete_prompt is None
            )
        ),
    )
