"""issues タブの D で開く削除確認 modal のレイアウト・描画と、開く/閉じる/確定する操作。"""

import requests
from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame

from redi.client import client
from redi.i18n import messages
from redi.tui.state import Renderable, TuiState


def render_delete_modal(state: TuiState) -> Renderable:
    modal = state.issue_tab.delete_modal
    parts: Renderable = []
    parts.append(
        (
            "",
            messages.tui_issue_delete_modal_target.format(
                id=modal.target_id, subject=modal.target_subject
            )
            + "\n\n",
        )
    )
    parts.append(
        (
            "",
            messages.tui_issue_delete_modal_prompt.format(expected=modal.target_id)
            + "\n",
        )
    )
    parts.append(("bold fg:ansicyan", messages.tui_issue_delete_modal_input_label))
    parts.append(("", modal.input_text))
    # 末尾の反転した空白を入力カーソルに見立てる
    parts.append(("reverse", " "))
    parts.append(("", "\n"))
    if modal.mismatch:
        parts.append(("fg:ansired", messages.tui_issue_delete_modal_mismatch + "\n"))
    parts.append(("", "\n"))
    parts.append(("", messages.tui_issue_delete_modal_hint))
    return parts


def build_delete_float(state: TuiState, show: FilterOrBool) -> Float:
    """削除確認 modal の Float を組み立てる。

    Frame を VSplit で挟んで左右に幅1の空白パディングを置く理由は
    `build_layout` の help_float 手前のコメントを参照。
    """
    return Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        Window(
                            FormattedTextControl(
                                lambda: render_delete_modal(state),
                                show_cursor=False,
                            ),
                            # 何を消すかが読めないと確認にならないので subject は折り返す
                            wrap_lines=True,
                        ),
                        title=lambda: messages.tui_issue_delete_modal_title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=show,
        ),
    )


def open_delete_modal(state: TuiState) -> bool:
    """カーソル位置の issue を対象に削除確認 modal を開く。対象がなければ False。"""
    issues = state.issue_tab.issues
    if not issues:
        return False
    issue = issues[state.issue_tab.cursor]
    issue_id = issue.get("id")
    if issue_id is None:
        return False
    modal = state.issue_tab.delete_modal
    modal.show = True
    modal.target_id = int(issue_id)
    modal.target_subject = str(issue.get("subject", ""))
    modal.input_text = ""
    modal.mismatch = False
    return True


def close_delete_modal(state: TuiState) -> None:
    """削除確認 modal を閉じて入力をクリアする。"""
    modal = state.issue_tab.delete_modal
    modal.show = False
    modal.input_text = ""
    modal.mismatch = False


def confirm_delete(state: TuiState) -> None:
    """modal で入力された issue_id が modal を開いた対象と一致したら削除する。

    入力が空の場合はまだ打ち始めていないだけなので何もしない。
    一致しない場合は modal.mismatch を立て、入力をクリアして再入力させる。
    削除成功時は modal を閉じ、ローカルの issue 一覧から該当行を取り除く。
    削除失敗時は modal を閉じて flash_message にエラーを出す。
    """
    modal = state.issue_tab.delete_modal
    entered = modal.input_text.strip()
    if not entered:
        return
    if entered != str(modal.target_id):
        modal.mismatch = True
        modal.input_text = ""
        return
    issues = state.issue_tab.issues
    index = next(
        (i for i, issue in enumerate(issues) if issue.get("id") == modal.target_id),
        None,
    )
    if index is None:
        close_delete_modal(state)
        return
    try:
        response = client.delete(f"/issues/{modal.target_id}.json")
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        close_delete_modal(state)
        state.flash_message = messages.tui_issue_delete_failed.format(error=e)
        return
    issues.pop(index)
    state.issue_tab.total_count = max(0, state.issue_tab.total_count - 1)
    if state.issue_tab.cursor >= len(issues):
        state.issue_tab.cursor = max(0, len(issues) - 1)
    close_delete_modal(state)


def input_digit(state: TuiState, digit: str) -> None:
    """入力欄に数字を1文字追加する。数字以外は無視する。"""
    if len(digit) != 1 or not digit.isdigit():
        return
    modal = state.issue_tab.delete_modal
    modal.input_text += digit
    modal.mismatch = False


def backspace(state: TuiState) -> None:
    """入力欄の末尾を1文字削る。"""
    modal = state.issue_tab.delete_modal
    if modal.input_text:
        modal.input_text = modal.input_text[:-1]
        modal.mismatch = False
