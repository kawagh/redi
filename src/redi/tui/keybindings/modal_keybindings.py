"""modal 表示中のキーバインド。"""

from prompt_toolkit.key_binding import KeyBindings

from redi.tui.choice_modal import register_choice_keys
from redi.tui.conditions import Conditions
from redi.tui.issue.delete_modal import (
    backspace as issue_delete_backspace,
)
from redi.tui.issue.delete_modal import (
    close_delete_modal as issue_close_delete_modal,
)
from redi.tui.issue.delete_modal import (
    confirm_delete as issue_confirm_delete,
)
from redi.tui.issue.delete_modal import (
    input_digit as issue_delete_input_digit,
)
from redi.tui.issue.issue_tab import reload_with_filter
from redi.tui.keybindings.keybinding_actions import reset_preview_scroll
from redi.tui.profile_modal import request_profile_switch
from redi.tui.project_modal import apply_project_switch
from redi.tui.state import IssueFilter, TimeEntryFilter, TuiState
from redi.tui.time_entry.time_entry_tab import (
    reload_with_filter as time_entry_reload_with_filter,
)


def register(kb: KeyBindings, state: TuiState, conditions: Conditions) -> None:
    show_help_modal = conditions.help_modal
    show_filter_modal = conditions.issue_filter_modal
    show_time_entry_filter_modal = conditions.time_entry_filter_modal
    show_error_modal = conditions.error_modal
    show_project_modal = conditions.project_modal
    show_issue_delete_modal = conditions.issue_delete_modal
    show_profile_modal = conditions.profile_modal

    @kb.add("<any>", filter=show_help_modal)
    def _(event):
        state.show_help = False

    @kb.add("q", filter=show_error_modal)
    def _(event):
        state.error_modal = None

    def _on_project_selected(event, project_id: str, label: str) -> None:
        reset_preview_scroll(state)
        apply_project_switch(state, project_id, label)

    register_choice_keys(
        kb, lambda: state.project_modal, show_project_modal, "p", _on_project_selected
    )

    def _on_profile_selected(event, name: str, _label: str) -> None:
        # 切替が必要なときだけ TUI を抜ける。適用と state のクリアは cli.main が行う。
        result = request_profile_switch(state, name)
        if result is not None:
            event.app.exit(result=result)

    register_choice_keys(
        kb, lambda: state.profile_modal, show_profile_modal, "P", _on_profile_selected
    )

    @kb.add("tab", filter=show_filter_modal)
    @kb.add("s-tab", filter=show_filter_modal)
    @kb.add("h", filter=show_filter_modal)
    @kb.add("l", filter=show_filter_modal)
    @kb.add("left", filter=show_filter_modal)
    @kb.add("right", filter=show_filter_modal)
    def _(event):
        modal = state.issue_tab.filter_modal
        modal.focus = "assignee" if modal.focus == "status" else "status"

    @kb.add("j", filter=show_filter_modal)
    @kb.add("down", filter=show_filter_modal)
    @kb.add("c-n", filter=show_filter_modal)
    def _issue_filter_modal_cursor_down(event):
        modal = state.issue_tab.filter_modal
        if modal.focus == "status":
            modal.status_cursor = min(
                len(modal.status_choices) - 1, modal.status_cursor + 1
            )
        else:
            modal.assignee_cursor = min(
                len(modal.assignee_choices) - 1, modal.assignee_cursor + 1
            )

    @kb.add("k", filter=show_filter_modal)
    @kb.add("up", filter=show_filter_modal)
    @kb.add("c-p", filter=show_filter_modal)
    def _issue_filter_modal_cursor_up(event):
        modal = state.issue_tab.filter_modal
        if modal.focus == "status":
            modal.status_cursor = max(0, modal.status_cursor - 1)
        else:
            modal.assignee_cursor = max(0, modal.assignee_cursor - 1)

    @kb.add("enter", filter=show_filter_modal)
    def _(event):
        modal = state.issue_tab.filter_modal
        if modal.focus == "status":
            if not modal.status_choices:
                return
            api_val, label = modal.status_choices[modal.status_cursor]
            state.issue_tab.filter.status_id = api_val
            state.issue_tab.filter.status_label = label
        else:
            if not modal.assignee_choices:
                return
            api_val, label = modal.assignee_choices[modal.assignee_cursor]
            state.issue_tab.filter.assigned_to_id = api_val
            state.issue_tab.filter.assigned_to_label = label
        reset_preview_scroll(state)
        reload_with_filter(state)

    @kb.add("c", filter=show_filter_modal)
    def _(event):
        state.issue_tab.filter = IssueFilter()
        modal = state.issue_tab.filter_modal
        modal.status_cursor = 0
        modal.assignee_cursor = 0
        reset_preview_scroll(state)
        reload_with_filter(state)

    @kb.add("escape", filter=show_filter_modal)
    @kb.add("f", filter=show_filter_modal)
    @kb.add("q", filter=show_filter_modal)
    def _(event):
        state.issue_tab.filter_modal.show = False

    @kb.add("j", filter=show_time_entry_filter_modal)
    @kb.add("down", filter=show_time_entry_filter_modal)
    @kb.add("c-n", filter=show_time_entry_filter_modal)
    def _time_entry_filter_modal_cursor_down(event):
        modal = state.time_entry_tab.filter_modal
        modal.user_cursor = min(len(modal.user_choices) - 1, modal.user_cursor + 1)

    @kb.add("k", filter=show_time_entry_filter_modal)
    @kb.add("up", filter=show_time_entry_filter_modal)
    @kb.add("c-p", filter=show_time_entry_filter_modal)
    def _time_entry_filter_modal_cursor_up(event):
        modal = state.time_entry_tab.filter_modal
        modal.user_cursor = max(0, modal.user_cursor - 1)

    @kb.add("enter", filter=show_time_entry_filter_modal)
    def _(event):
        modal = state.time_entry_tab.filter_modal
        if not modal.user_choices:
            return
        api_val, label = modal.user_choices[modal.user_cursor]
        state.time_entry_tab.filter.user_id = api_val
        if api_val is not None:
            state.time_entry_tab.filter.user_label = label
        reset_preview_scroll(state)
        time_entry_reload_with_filter(state)
        modal.show = False

    @kb.add("c", filter=show_time_entry_filter_modal)
    def _(event):
        state.time_entry_tab.filter = TimeEntryFilter(user_id=None, user_label="")
        modal = state.time_entry_tab.filter_modal
        modal.user_cursor = 0
        reset_preview_scroll(state)
        time_entry_reload_with_filter(state)

    @kb.add("escape", filter=show_time_entry_filter_modal)
    @kb.add("f", filter=show_time_entry_filter_modal)
    @kb.add("q", filter=show_time_entry_filter_modal)
    def _(event):
        state.time_entry_tab.filter_modal.show = False

    @kb.add("enter", filter=show_issue_delete_modal)
    def _(event):
        issue_confirm_delete(state)

    @kb.add("escape", filter=show_issue_delete_modal)
    @kb.add("c-c", filter=show_issue_delete_modal)
    def _(event):
        issue_close_delete_modal(state)

    @kb.add("backspace", filter=show_issue_delete_modal)
    def _(event):
        issue_delete_backspace(state)

    # id 入力欄なので数字だけ受け付ける
    for digit in "0123456789":

        @kb.add(digit, filter=show_issue_delete_modal)
        def _(event):
            issue_delete_input_digit(state, event.data)
