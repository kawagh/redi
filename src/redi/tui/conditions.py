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
    help_dialog: Condition
    issue_filter_dialog: Condition
    issue_find_dialog: Condition
    issue_delete_dialog: Condition
    wiki_delete_dialog: Condition
    wiki_version_dialog: Condition
    wiki_diff_dialog: Condition
    time_entry_filter_dialog: Condition
    error_dialog: Condition
    project_dialog: Condition
    profile_dialog: Condition
    comment_select: Condition


def build_conditions(state: TuiState) -> Conditions:
    return Conditions(
        normal=Condition(
            lambda: (
                not state.search_mode
                and state.confirm_delete_prompt is None
                and not state.show_help
                and not state.issue_tab.filter_dialog.show
                and not state.issue_tab.find_dialog.show
                and not state.issue_tab.delete_dialog.show
                and not state.wiki_tab.delete_dialog.show
                and not state.wiki_tab.version_dialog.show
                and not state.wiki_tab.diff_dialog.show
                and not state.time_entry_tab.filter_dialog.show
                and state.error_dialog is None
                and not state.issue_tab.comment_select.active
                and not state.project_dialog.show
                and not state.profile_dialog.show
            )
        ),
        search=Condition(lambda: state.search_mode),
        confirm_delete=Condition(lambda: state.confirm_delete_prompt is not None),
        help_dialog=Condition(lambda: state.show_help),
        issue_filter_dialog=Condition(lambda: state.issue_tab.filter_dialog.show),
        issue_find_dialog=Condition(lambda: state.issue_tab.find_dialog.show),
        issue_delete_dialog=Condition(lambda: state.issue_tab.delete_dialog.show),
        wiki_delete_dialog=Condition(lambda: state.wiki_tab.delete_dialog.show),
        wiki_version_dialog=Condition(lambda: state.wiki_tab.version_dialog.show),
        wiki_diff_dialog=Condition(lambda: state.wiki_tab.diff_dialog.show),
        time_entry_filter_dialog=Condition(
            lambda: state.time_entry_tab.filter_dialog.show
        ),
        error_dialog=Condition(lambda: state.error_dialog is not None),
        project_dialog=Condition(lambda: state.project_dialog.show),
        profile_dialog=Condition(lambda: state.profile_dialog.show),
        comment_select=Condition(
            lambda: (
                state.issue_tab.comment_select.active
                and state.confirm_delete_prompt is None
            )
        ),
    )
