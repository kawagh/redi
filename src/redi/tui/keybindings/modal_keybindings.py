"""modal 表示中のキーバインド。

modal を開く `f` / `p` も、開いたあとの操作と近い場所に置きたいのでここで登録する。
"""

from prompt_toolkit.key_binding import KeyBindings

from redi.tui.choices import (
    build_assignee_choices,
    build_status_choices,
    build_user_choices,
)
from redi.tui.issue.issue_tab import reload_with_filter
from redi.tui.keybindings.keybinding_conditions import (
    Conditions,
    clear_temporary_state,
    reset_preview_scroll,
)
from redi.tui.project_modal import apply_project_switch, open_project_modal
from redi.tui.state import IssueFilter, TimeEntryFilter, TuiState
from redi.tui.time_entry.time_entry_tab import (
    reload_with_filter as time_entry_reload_with_filter,
)


def register(kb: KeyBindings, state: TuiState, conditions: Conditions) -> None:
    normal_mode = conditions.normal
    show_help_modal = conditions.help_modal
    show_filter_modal = conditions.issue_filter_modal
    show_time_entry_filter_modal = conditions.time_entry_filter_modal
    show_error_modal = conditions.error_modal
    show_project_modal = conditions.project_modal

    @kb.add("<any>", filter=show_help_modal)
    def _(event):
        state.show_help = False

    @kb.add("q", filter=show_error_modal)
    def _(event):
        state.error_modal = None

    def _open_filter_modal() -> None:
        modal = state.issue_tab.filter_modal
        modal.status_choices = build_status_choices()
        modal.assignee_choices = build_assignee_choices(
            state.effective_project_id(), state.me_id
        )
        modal.status_cursor = 0
        for idx, (api_val, _label) in enumerate(modal.status_choices):
            if api_val == state.issue_tab.filter.status_id:
                modal.status_cursor = idx
                break
        modal.assignee_cursor = 0
        for idx, (api_val, _label) in enumerate(modal.assignee_choices):
            if api_val == state.issue_tab.filter.assigned_to_id:
                modal.assignee_cursor = idx
                break
        modal.focus = "status"
        modal.show = True

    def _open_time_entry_filter_modal() -> None:
        modal = state.time_entry_tab.filter_modal
        modal.user_choices = build_user_choices(
            state.effective_project_id(), state.me_id
        )
        modal.user_cursor = 0
        for idx, (api_val, _label) in enumerate(modal.user_choices):
            if api_val == state.time_entry_tab.filter.user_id:
                modal.user_cursor = idx
                break
        modal.show = True

    @kb.add("f", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        if state.tab == "issues":
            _open_filter_modal()
        elif state.tab == "time_entries":
            _open_time_entry_filter_modal()

    @kb.add("p", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        open_project_modal(state)

    @kb.add("j", filter=show_project_modal)
    @kb.add("down", filter=show_project_modal)
    @kb.add("c-n", filter=show_project_modal)
    def _project_modal_cursor_down(event):
        modal = state.project_modal
        modal.cursor = min(len(modal.choices) - 1, modal.cursor + 1)

    @kb.add("k", filter=show_project_modal)
    @kb.add("up", filter=show_project_modal)
    @kb.add("c-p", filter=show_project_modal)
    def _project_modal_cursor_up(event):
        modal = state.project_modal
        modal.cursor = max(0, modal.cursor - 1)

    @kb.add("enter", filter=show_project_modal)
    def _(event):
        modal = state.project_modal
        if not modal.choices:
            return
        pid, label = modal.choices[modal.cursor]
        reset_preview_scroll(state)
        apply_project_switch(state, pid, label)

    @kb.add("escape", filter=show_project_modal)
    @kb.add("p", filter=show_project_modal)
    @kb.add("q", filter=show_project_modal)
    def _(event):
        state.project_modal.show = False

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
