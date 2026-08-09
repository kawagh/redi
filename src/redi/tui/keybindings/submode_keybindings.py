"""通常モードから入るサブモード (コメント選択/削除確認/検索) のキーバインド。

modal は開かず、一覧の表示はそのままにキーの解釈だけが変わるものをまとめる。
"""

from prompt_toolkit.key_binding import KeyBindings

from redi.tui.issue.issue_tab import (
    comment_select_cursor_down,
    comment_select_cursor_up,
    confirm_comment_delete,
    confirm_comment_edit,
    exit_comment_select_mode,
    request_comment_delete,
)
from redi.tui.keybindings.keybinding_conditions import (
    Conditions,
    reset_preview_scroll,
    scroll_preview,
)
from redi.tui.state import TuiState
from redi.tui.tabs import TABS
from redi.tui.time_entry.time_entry_tab import (
    confirm_delete as time_entry_confirm_delete,
)


def register(kb: KeyBindings, state: TuiState, conditions: Conditions) -> None:
    search_mode = conditions.search
    confirm_delete_mode = conditions.confirm_delete
    comment_select_mode = conditions.comment_select

    # issueTab;コメント選択モード
    @kb.add("up", filter=comment_select_mode)
    @kb.add("k", filter=comment_select_mode)
    @kb.add("c-p", filter=comment_select_mode)
    def _(event):
        comment_select_cursor_up(state)

    @kb.add("down", filter=comment_select_mode)
    @kb.add("j", filter=comment_select_mode)
    @kb.add("c-n", filter=comment_select_mode)
    def _(event):
        comment_select_cursor_down(state)

    @kb.add("c-d", filter=comment_select_mode)
    def _(event):
        scroll_preview(state, max(1, state.page_size // 2))

    @kb.add("c-u", filter=comment_select_mode)
    def _(event):
        scroll_preview(state, -max(1, state.page_size // 2))

    @kb.add("u", filter=comment_select_mode)
    def _(event):
        result = confirm_comment_edit(state)
        if result is not None:
            exit_comment_select_mode(state)
            event.app.exit(result=result)

    @kb.add("D", filter=comment_select_mode)
    def _(event):
        prompt = request_comment_delete(state)
        if prompt is not None:
            state.confirm_delete_prompt = prompt

    @kb.add("enter", filter=comment_select_mode)
    def _(event):
        pass

    @kb.add("escape", filter=comment_select_mode)
    @kb.add("q", filter=comment_select_mode)
    def _(event):
        exit_comment_select_mode(state)

    @kb.add("y", filter=confirm_delete_mode)
    @kb.add("Y", filter=confirm_delete_mode)
    def _(event):
        state.confirm_delete_prompt = None
        if state.tab == "time_entries":
            time_entry_confirm_delete(state)
        elif state.tab == "issues" and state.issue_tab.comment_select.active:
            result = confirm_comment_delete(state)
            if result is not None:
                exit_comment_select_mode(state)
                event.app.exit(result=result)

    @kb.add("<any>", filter=confirm_delete_mode)
    def _(event):
        state.confirm_delete_prompt = None

    @kb.add("enter", filter=search_mode)
    def _(event):
        if state.search_query:
            reset_preview_scroll(state)
            TABS[state.tab].on_search(state, state.search_query)
        state.search_mode = False

    @kb.add("escape", filter=search_mode)
    @kb.add("c-c", filter=search_mode)
    def _(event):
        state.search_mode = False
        state.search_query = ""

    @kb.add("backspace", filter=search_mode)
    def _(event):
        if state.search_query:
            state.search_query = state.search_query[:-1]
        else:
            state.search_mode = False

    @kb.add("<any>", filter=search_mode)
    def _(event):
        data = event.data
        if data and len(data) == 1 and data.isprintable():
            state.search_query += data
