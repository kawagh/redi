"""modal 表示中のキーバインド。"""

from string import ascii_uppercase

from prompt_toolkit.key_binding import KeyBindings

from redi.tui.choice_dialog import register_choice_keys
from redi.tui.conditions import Conditions
from redi.tui.issue.delete_dialog import (
    backspace as issue_delete_backspace,
)
from redi.tui.issue.delete_dialog import (
    close_delete_dialog as issue_close_delete_dialog,
)
from redi.tui.issue.delete_dialog import (
    confirm_delete as issue_confirm_delete,
)
from redi.tui.issue.delete_dialog import (
    input_digit as issue_delete_input_digit,
)
from redi.tui.issue.filter_dialog import (
    section_choices,
    section_cursor,
    set_section_cursor,
    shift_focus,
    sync_cursors_to_filter,
)
from redi.tui.issue.find_dialog import (
    backspace as find_backspace,
)
from redi.tui.issue.find_dialog import (
    clear_input as find_clear_input,
)
from redi.tui.issue.find_dialog import (
    close_find_dialog,
    confirm_find,
)
from redi.tui.issue.find_dialog import (
    delete_word as find_delete_word,
)
from redi.tui.issue.find_dialog import (
    input_char as find_input_char,
)
from redi.tui.issue.issue_tab import clear_find_for_filter, reload_with_filter
from redi.tui.keybindings.keybinding_actions import reset_preview_scroll
from redi.tui.profile_dialog import request_profile_switch
from redi.tui.project_dialog import apply_project_switch
from redi.tui.state import TuiState
from redi.tui.state.issue_tab import IssueFilter
from redi.tui.state.time_entry_tab import TimeEntryFilter
from redi.tui.time_entry.time_entry_tab import (
    reload_with_filter as time_entry_reload_with_filter,
)
from redi.tui.wiki.delete_dialog import (
    backspace as wiki_delete_backspace,
)
from redi.tui.wiki.delete_dialog import (
    close_delete_dialog as wiki_close_delete_dialog,
)
from redi.tui.wiki.delete_dialog import (
    confirm_delete as wiki_confirm_delete,
)
from redi.tui.wiki.delete_dialog import (
    input_char as wiki_delete_input_char,
)
from redi.tui.wiki.diff_dialog import (
    apply_diff as wiki_apply_diff,
)
from redi.tui.wiki.diff_dialog import (
    clear_diff as wiki_clear_diff,
)
from redi.tui.wiki.diff_dialog import (
    move_cursor as wiki_diff_move_cursor,
)
from redi.tui.wiki.diff_dialog import (
    move_cursor_to_end as wiki_diff_move_cursor_to_end,
)
from redi.tui.wiki.diff_dialog import (
    shift_focus as wiki_diff_shift_focus,
)
from redi.tui.wiki.version_dialog import select_version as wiki_select_version


def register(kb: KeyBindings, state: TuiState, conditions: Conditions) -> None:
    show_help_dialog = conditions.help_dialog
    show_filter_dialog = conditions.issue_filter_dialog
    show_time_entry_filter_dialog = conditions.time_entry_filter_dialog
    show_error_dialog = conditions.error_dialog
    show_project_dialog = conditions.project_dialog
    show_issue_delete_dialog = conditions.issue_delete_dialog
    show_wiki_delete_dialog = conditions.wiki_delete_dialog
    show_find_dialog = conditions.issue_find_dialog
    show_profile_dialog = conditions.profile_dialog
    show_wiki_version_dialog = conditions.wiki_version_dialog
    show_wiki_diff_dialog = conditions.wiki_diff_dialog

    @kb.add("<any>", filter=show_help_dialog)
    def _(event):
        state.show_help = False

    @kb.add("q", filter=show_error_dialog)
    def _(event):
        state.error_dialog = None

    def _on_project_selected(event, project_id: str, label: str) -> None:
        reset_preview_scroll(state)
        apply_project_switch(state, project_id, label)

    register_choice_keys(
        kb, lambda: state.project_dialog, show_project_dialog, "p", _on_project_selected
    )

    def _on_profile_selected(event, name: str, _label: str) -> None:
        # 切替が必要なときだけ TUI を抜ける。適用と state のクリアは cli.main が行う。
        result = request_profile_switch(state, name)
        if result is not None:
            event.app.exit(result=result)

    register_choice_keys(
        kb, lambda: state.profile_dialog, show_profile_dialog, "P", _on_profile_selected
    )

    def _on_wiki_version_selected(event, value: str, _label: str) -> None:
        reset_preview_scroll(state)
        wiki_select_version(state, int(value))
        state.wiki_tab.version_dialog.show = False

    register_choice_keys(
        kb,
        lambda: state.wiki_tab.version_dialog,
        show_wiki_version_dialog,
        "h",
        _on_wiki_version_selected,
    )

    @kb.add("tab", filter=show_wiki_diff_dialog)
    @kb.add("l", filter=show_wiki_diff_dialog)
    @kb.add("right", filter=show_wiki_diff_dialog)
    def _wiki_diff_dialog_focus_next(event):
        dialog = state.wiki_tab.diff_dialog
        dialog.focus = wiki_diff_shift_focus(dialog.focus, 1)

    @kb.add("s-tab", filter=show_wiki_diff_dialog)
    @kb.add("h", filter=show_wiki_diff_dialog)
    @kb.add("left", filter=show_wiki_diff_dialog)
    def _wiki_diff_dialog_focus_prev(event):
        dialog = state.wiki_tab.diff_dialog
        dialog.focus = wiki_diff_shift_focus(dialog.focus, -1)

    @kb.add("j", filter=show_wiki_diff_dialog)
    @kb.add("down", filter=show_wiki_diff_dialog)
    @kb.add("c-n", filter=show_wiki_diff_dialog)
    def _wiki_diff_dialog_cursor_down(event):
        wiki_diff_move_cursor(state.wiki_tab.diff_dialog, 1)

    @kb.add("k", filter=show_wiki_diff_dialog)
    @kb.add("up", filter=show_wiki_diff_dialog)
    @kb.add("c-p", filter=show_wiki_diff_dialog)
    def _wiki_diff_dialog_cursor_up(event):
        wiki_diff_move_cursor(state.wiki_tab.diff_dialog, -1)

    @kb.add("g", "g", filter=show_wiki_diff_dialog)
    def _wiki_diff_dialog_cursor_top(event):
        wiki_diff_move_cursor_to_end(state.wiki_tab.diff_dialog, top=True)

    @kb.add("G", filter=show_wiki_diff_dialog)
    def _wiki_diff_dialog_cursor_bottom(event):
        wiki_diff_move_cursor_to_end(state.wiki_tab.diff_dialog, top=False)

    @kb.add("enter", filter=show_wiki_diff_dialog)
    def _wiki_diff_dialog_apply(event):
        if wiki_apply_diff(state):
            reset_preview_scroll(state)

    @kb.add("c", filter=show_wiki_diff_dialog)
    def _wiki_diff_dialog_clear(event):
        wiki_clear_diff(state)
        reset_preview_scroll(state)

    @kb.add("escape", filter=show_wiki_diff_dialog)
    @kb.add("d", filter=show_wiki_diff_dialog)
    @kb.add("q", filter=show_wiki_diff_dialog)
    def _wiki_diff_dialog_close(event):
        state.wiki_tab.diff_dialog.show = False

    @kb.add("tab", filter=show_filter_dialog)
    @kb.add("l", filter=show_filter_dialog)
    @kb.add("right", filter=show_filter_dialog)
    def _issue_filter_dialog_focus_next(event):
        dialog = state.issue_tab.filter_dialog
        dialog.focus = shift_focus(dialog.focus, 1)

    @kb.add("s-tab", filter=show_filter_dialog)
    @kb.add("h", filter=show_filter_dialog)
    @kb.add("left", filter=show_filter_dialog)
    def _issue_filter_dialog_focus_prev(event):
        dialog = state.issue_tab.filter_dialog
        dialog.focus = shift_focus(dialog.focus, -1)

    @kb.add("j", filter=show_filter_dialog)
    @kb.add("down", filter=show_filter_dialog)
    @kb.add("c-n", filter=show_filter_dialog)
    def _issue_filter_dialog_cursor_down(event):
        dialog = state.issue_tab.filter_dialog
        choices = section_choices(dialog, dialog.focus)
        set_section_cursor(
            dialog,
            dialog.focus,
            min(len(choices) - 1, section_cursor(dialog, dialog.focus) + 1),
        )

    @kb.add("k", filter=show_filter_dialog)
    @kb.add("up", filter=show_filter_dialog)
    @kb.add("c-p", filter=show_filter_dialog)
    def _issue_filter_dialog_cursor_up(event):
        dialog = state.issue_tab.filter_dialog
        set_section_cursor(
            dialog, dialog.focus, max(0, section_cursor(dialog, dialog.focus) - 1)
        )

    @kb.add("enter", filter=show_filter_dialog)
    def _issue_filter_dialog_apply(event):
        dialog = state.issue_tab.filter_dialog
        choices = section_choices(dialog, dialog.focus)
        if not choices:
            return
        api_val, label = choices[section_cursor(dialog, dialog.focus)]
        # クエリと status/assignee/tracker の排他は IssueFilter.apply が持つ。
        state.issue_tab.filter.apply(dialog.focus, api_val, label)
        sync_cursors_to_filter(state)
        reset_preview_scroll(state)
        clear_find_for_filter(state)
        reload_with_filter(state)

    @kb.add("c", filter=show_filter_dialog)
    def _issue_filter_dialog_clear(event):
        state.issue_tab.filter = IssueFilter()
        dialog = state.issue_tab.filter_dialog
        dialog.status_cursor = 0
        dialog.assignee_cursor = 0
        dialog.tracker_cursor = 0
        dialog.query_cursor = 0
        reset_preview_scroll(state)
        clear_find_for_filter(state)
        reload_with_filter(state)

    @kb.add("escape", filter=show_filter_dialog)
    @kb.add("f", filter=show_filter_dialog)
    @kb.add("q", filter=show_filter_dialog)
    def _(event):
        state.issue_tab.filter_dialog.show = False

    @kb.add("j", filter=show_time_entry_filter_dialog)
    @kb.add("down", filter=show_time_entry_filter_dialog)
    @kb.add("c-n", filter=show_time_entry_filter_dialog)
    def _time_entry_filter_dialog_cursor_down(event):
        dialog = state.time_entry_tab.filter_dialog
        dialog.user_cursor = min(len(dialog.user_choices) - 1, dialog.user_cursor + 1)

    @kb.add("k", filter=show_time_entry_filter_dialog)
    @kb.add("up", filter=show_time_entry_filter_dialog)
    @kb.add("c-p", filter=show_time_entry_filter_dialog)
    def _time_entry_filter_dialog_cursor_up(event):
        dialog = state.time_entry_tab.filter_dialog
        dialog.user_cursor = max(0, dialog.user_cursor - 1)

    @kb.add("enter", filter=show_time_entry_filter_dialog)
    def _(event):
        dialog = state.time_entry_tab.filter_dialog
        if not dialog.user_choices:
            return
        api_val, label = dialog.user_choices[dialog.user_cursor]
        state.time_entry_tab.filter.user_id = api_val
        if api_val is not None:
            state.time_entry_tab.filter.user_label = label
        reset_preview_scroll(state)
        time_entry_reload_with_filter(state)
        dialog.show = False

    @kb.add("c", filter=show_time_entry_filter_dialog)
    def _(event):
        state.time_entry_tab.filter = TimeEntryFilter(user_id=None, user_label="")
        dialog = state.time_entry_tab.filter_dialog
        dialog.user_cursor = 0
        reset_preview_scroll(state)
        time_entry_reload_with_filter(state)

    @kb.add("escape", filter=show_time_entry_filter_dialog)
    @kb.add("f", filter=show_time_entry_filter_dialog)
    @kb.add("q", filter=show_time_entry_filter_dialog)
    def _(event):
        state.time_entry_tab.filter_dialog.show = False

    @kb.add("enter", filter=show_issue_delete_dialog)
    def _(event):
        issue_confirm_delete(state)

    @kb.add("escape", filter=show_issue_delete_dialog)
    @kb.add("c-c", filter=show_issue_delete_dialog)
    def _(event):
        issue_close_delete_dialog(state)

    @kb.add("backspace", filter=show_issue_delete_dialog)
    def _(event):
        issue_delete_backspace(state)

    # id 入力欄なので数字だけ受け付ける
    for digit in "0123456789":

        @kb.add(digit, filter=show_issue_delete_dialog)
        def _(event):
            issue_delete_input_digit(state, event.data)

    @kb.add("enter", filter=show_find_dialog)
    def _(event):
        confirm_find(state)

    @kb.add("escape", filter=show_find_dialog)
    @kb.add("c-c", filter=show_find_dialog)
    def _(event):
        close_find_dialog(state)

    @kb.add("backspace", filter=show_find_dialog)
    def _(event):
        find_backspace(state)

    @kb.add("c-w", filter=show_find_dialog)
    def _(event):
        find_delete_word(state)

    @kb.add("c-u", filter=show_find_dialog)
    def _(event):
        find_clear_input(state)

    # 検索クエリは自由入力なので、印字できる1文字はそのまま受け付ける
    @kb.add("<any>", filter=show_find_dialog)
    def _(event):
        data = event.data
        if data and len(data) == 1 and data.isprintable():
            find_input_char(state, data)

    @kb.add("enter", filter=show_wiki_delete_dialog)
    def _(event):
        wiki_confirm_delete(state)

    @kb.add("escape", filter=show_wiki_delete_dialog)
    @kb.add("c-c", filter=show_wiki_delete_dialog)
    def _(event):
        wiki_close_delete_dialog(state)

    @kb.add("backspace", filter=show_wiki_delete_dialog)
    def _(event):
        wiki_delete_backspace(state)

    # 確認語 (DELETE) の入力欄なので英大文字だけ受け付ける。打ち間違いも入力欄に
    # 残して不一致として気付けるようにする。
    for char in ascii_uppercase:

        @kb.add(char, filter=show_wiki_delete_dialog)
        def _(event):
            wiki_delete_input_char(state, event.data)
