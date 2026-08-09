"""通常モード (modal を開いていない一覧操作中) のキーバインド。"""

from prompt_toolkit.key_binding import KeyBindings

from redi.i18n import messages
from redi.tui.issue.filter_modal import open_filter_modal as open_issue_filter_modal
from redi.tui.keybindings.keybinding_conditions import (
    Conditions,
    clear_temporary_state,
    reset_preview_scroll,
    scroll_preview,
)
from redi.tui.project_modal import open_project_modal
from redi.tui.state import TuiState
from redi.tui.tabs import TABS
from redi.tui.time_entry.filter_modal import (
    open_filter_modal as open_time_entry_filter_modal,
)
from redi.tui.time_entry.time_entry_tab import (
    request_delete as time_entry_request_delete,
)


def register(kb: KeyBindings, state: TuiState, conditions: Conditions) -> None:
    normal_mode = conditions.normal

    @kb.add("tab", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        reset_preview_scroll(state)
        tab_keys = list(TABS.keys())
        idx = tab_keys.index(state.tab)
        state.tab = tab_keys[(idx + 1) % len(tab_keys)]
        TABS[state.tab].on_activate(state)

    @kb.add("s-tab", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        reset_preview_scroll(state)
        tab_keys = list(TABS.keys())
        idx = tab_keys.index(state.tab)
        state.tab = tab_keys[(idx - 1) % len(tab_keys)]
        TABS[state.tab].on_activate(state)

    @kb.add("up", filter=normal_mode)
    @kb.add("k", filter=normal_mode)
    @kb.add("c-p", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        reset_preview_scroll(state)
        TABS[state.tab].on_up(state)

    @kb.add("down", filter=normal_mode)
    @kb.add("j", filter=normal_mode)
    @kb.add("c-n", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        reset_preview_scroll(state)
        TABS[state.tab].on_down(state)

    @kb.add("g", "g", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        reset_preview_scroll(state)
        TABS[state.tab].on_goto_top(state)

    @kb.add("G", filter=normal_mode)
    def _(event):
        if state.number_buffer:
            try:
                target_id = int(state.number_buffer)
            except ValueError:
                target_id = None
            clear_temporary_state(state)
            reset_preview_scroll(state)
            if target_id is not None:
                TABS[state.tab].on_jump_to_id(state, target_id)
        else:
            reset_preview_scroll(state)
            TABS[state.tab].on_goto_bottom(state)

    for digit in "0123456789":

        @kb.add(digit, filter=normal_mode)
        def _(event, digit=digit):
            # 先頭 0 は無視 (多桁数字の中では許容)。
            if not state.number_buffer and digit == "0":
                return
            state.number_buffer += digit

    @kb.add("right", filter=normal_mode)
    @kb.add("l", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        reset_preview_scroll(state)
        TABS[state.tab].on_page_forward(state)

    @kb.add("left", filter=normal_mode)
    @kb.add("h", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        reset_preview_scroll(state)
        TABS[state.tab].on_page_backward(state)

    @kb.add("c-e", filter=normal_mode)
    def _(event):
        scroll_preview(state, 1)

    @kb.add("c-y", filter=normal_mode)
    def _(event):
        scroll_preview(state, -1)

    @kb.add("c-d", filter=normal_mode)
    def _(event):
        scroll_preview(state, max(1, state.page_size // 2))

    @kb.add("c-u", filter=normal_mode)
    def _(event):
        scroll_preview(state, -max(1, state.page_size // 2))

    @kb.add("enter", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        TABS[state.tab].on_enter(state)

    @kb.add("v", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        TABS[state.tab].on_open_web(state)

    @kb.add("V", filter=normal_mode)
    def _(event):
        if state.number_buffer:
            try:
                target_id = int(state.number_buffer)
            except ValueError:
                target_id = None
            clear_temporary_state(state)
            if target_id is not None:
                TABS[state.tab].on_open_web_by_id(state, target_id)

    for action_key in ("u", "c", "t"):

        @kb.add(action_key, filter=normal_mode)
        def _(event, action_key=action_key):
            clear_temporary_state(state)
            result = TABS[state.tab].on_action_key(state, action_key)
            if result is not None:
                event.app.exit(result=result)

    @kb.add("n", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        if state.search_query:
            reset_preview_scroll(state)
            TABS[state.tab].on_search(state, state.search_query, forward=True)
            return
        result = TABS[state.tab].on_action_key(state, "n")
        if result is not None:
            event.app.exit(result=result)

    @kb.add("N", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        if state.search_query:
            reset_preview_scroll(state)
            TABS[state.tab].on_search(state, state.search_query, forward=False)

    @kb.add("/", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        state.search_mode = True
        state.search_query = ""

    @kb.add("D", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        if state.tab != "time_entries":
            return
        prompt = time_entry_request_delete(state)
        if prompt is not None:
            state.confirm_delete_prompt = prompt

    @kb.add("R", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        reset_preview_scroll(state)
        TABS[state.tab].on_reload(state)
        state.flash_message = messages.tui_flash_reloaded

    @kb.add("q", filter=normal_mode)
    @kb.add("c-c", filter=normal_mode)
    def _(event):
        event.app.exit(result=None)

    @kb.add("?", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        state.show_help = True

    @kb.add("f", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        if state.tab == "issues":
            open_issue_filter_modal(state)
        elif state.tab == "time_entries":
            open_time_entry_filter_modal(state)

    @kb.add("p", filter=normal_mode)
    def _(event):
        clear_temporary_state(state)
        open_project_modal(state)
