"""modal 表示中のキーバインド。"""

from string import ascii_uppercase

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
from redi.tui.issue.filter_modal import (
    section_choices,
    section_cursor,
    set_section_cursor,
    shift_focus,
    sync_cursors_to_filter,
)
from redi.tui.issue.issue_tab import reload_with_filter
from redi.tui.keybindings.keybinding_actions import reset_preview_scroll
from redi.tui.loading import run_with_spinner
from redi.tui.profile_modal import request_profile_switch
from redi.tui.project_modal import apply_project_switch
from redi.tui.state import IssueFilter, TimeEntryFilter, TuiState
from redi.tui.tabs import TABS
from redi.tui.time_entry.time_entry_tab import (
    reload_with_filter as time_entry_reload_with_filter,
)
from redi.tui.wiki.delete_modal import (
    backspace as wiki_delete_backspace,
)
from redi.tui.wiki.delete_modal import (
    close_delete_modal as wiki_close_delete_modal,
)
from redi.tui.wiki.delete_modal import (
    confirm_delete as wiki_confirm_delete,
)
from redi.tui.wiki.delete_modal import (
    input_char as wiki_delete_input_char,
)


def register(kb: KeyBindings, state: TuiState, conditions: Conditions) -> None:
    show_help_modal = conditions.help_modal
    show_filter_modal = conditions.issue_filter_modal
    show_time_entry_filter_modal = conditions.time_entry_filter_modal
    show_error_modal = conditions.error_modal
    show_project_modal = conditions.project_modal
    show_issue_delete_modal = conditions.issue_delete_modal
    show_wiki_delete_modal = conditions.wiki_delete_modal
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
    @kb.add("l", filter=show_filter_modal)
    @kb.add("right", filter=show_filter_modal)
    def _issue_filter_modal_focus_next(event):
        modal = state.issue_tab.filter_modal
        modal.focus = shift_focus(modal.focus, 1)

    @kb.add("s-tab", filter=show_filter_modal)
    @kb.add("h", filter=show_filter_modal)
    @kb.add("left", filter=show_filter_modal)
    def _issue_filter_modal_focus_prev(event):
        modal = state.issue_tab.filter_modal
        modal.focus = shift_focus(modal.focus, -1)

    @kb.add("j", filter=show_filter_modal)
    @kb.add("down", filter=show_filter_modal)
    @kb.add("c-n", filter=show_filter_modal)
    def _issue_filter_modal_cursor_down(event):
        modal = state.issue_tab.filter_modal
        choices = section_choices(modal, modal.focus)
        set_section_cursor(
            modal,
            modal.focus,
            min(len(choices) - 1, section_cursor(modal, modal.focus) + 1),
        )

    @kb.add("k", filter=show_filter_modal)
    @kb.add("up", filter=show_filter_modal)
    @kb.add("c-p", filter=show_filter_modal)
    def _issue_filter_modal_cursor_up(event):
        modal = state.issue_tab.filter_modal
        set_section_cursor(
            modal, modal.focus, max(0, section_cursor(modal, modal.focus) - 1)
        )

    async def _reload_issues_with_spinner(event) -> None:
        await run_with_spinner(
            state,
            event.app,
            "list",
            TABS["issues"].loading_label,
            lambda: reload_with_filter(state),
        )

    @kb.add("enter", filter=show_filter_modal & ~conditions.loading)
    async def _issue_filter_modal_apply(event):
        modal = state.issue_tab.filter_modal
        choices = section_choices(modal, modal.focus)
        if not choices:
            return
        api_val, label = choices[section_cursor(modal, modal.focus)]
        # クエリと status/assignee/tracker の排他は IssueFilter.apply が持つ。
        state.issue_tab.filter.apply(modal.focus, api_val, label)
        sync_cursors_to_filter(state)
        reset_preview_scroll(state)
        await _reload_issues_with_spinner(event)

    @kb.add("c", filter=show_filter_modal & ~conditions.loading)
    async def _issue_filter_modal_clear(event):
        state.issue_tab.filter = IssueFilter()
        modal = state.issue_tab.filter_modal
        modal.status_cursor = 0
        modal.assignee_cursor = 0
        modal.tracker_cursor = 0
        modal.query_cursor = 0
        reset_preview_scroll(state)
        await _reload_issues_with_spinner(event)

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

    async def _reload_time_entries_with_spinner(event) -> None:
        await run_with_spinner(
            state,
            event.app,
            "list",
            TABS["time_entries"].loading_label,
            lambda: time_entry_reload_with_filter(state),
        )

    @kb.add("enter", filter=show_time_entry_filter_modal & ~conditions.loading)
    async def _(event):
        modal = state.time_entry_tab.filter_modal
        if not modal.user_choices:
            return
        api_val, label = modal.user_choices[modal.user_cursor]
        state.time_entry_tab.filter.user_id = api_val
        if api_val is not None:
            state.time_entry_tab.filter.user_label = label
        reset_preview_scroll(state)
        await _reload_time_entries_with_spinner(event)
        modal.show = False

    @kb.add("c", filter=show_time_entry_filter_modal & ~conditions.loading)
    async def _(event):
        state.time_entry_tab.filter = TimeEntryFilter(user_id=None, user_label="")
        modal = state.time_entry_tab.filter_modal
        modal.user_cursor = 0
        reset_preview_scroll(state)
        await _reload_time_entries_with_spinner(event)

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

    @kb.add("enter", filter=show_wiki_delete_modal)
    def _(event):
        wiki_confirm_delete(state)

    @kb.add("escape", filter=show_wiki_delete_modal)
    @kb.add("c-c", filter=show_wiki_delete_modal)
    def _(event):
        wiki_close_delete_modal(state)

    @kb.add("backspace", filter=show_wiki_delete_modal)
    def _(event):
        wiki_delete_backspace(state)

    # 確認語 (DELETE) の入力欄なので英大文字だけ受け付ける。打ち間違いも入力欄に
    # 残して不一致として気付けるようにする。
    for char in ascii_uppercase:

        @kb.add(char, filter=show_wiki_delete_modal)
        def _(event):
            wiki_delete_input_char(state, event.data)
