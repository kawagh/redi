"""issues タブの D で開く削除確認 modal のレイアウト・描画と、開く/閉じる/確定する操作。

issue は数値 id を持つため、対象の issue_id を打ち直させて確定する。
HTTP は `service.issue_service` に任せ、ここでは入力の検証と状態の更新だけを行う。
"""

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

from redi.api.issue import IssueNotFoundException
from redi.i18n import messages
from redi.service import issue_service
from redi.tui.state import IssueDeleteModalState, Renderable, TuiState


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
    if modal.notice:
        parts.append(("fg:ansired", modal.notice + "\n"))
    parts.append(("", "\n"))
    parts.append(("", messages.tui_issue_delete_modal_hint))
    return parts


def build_delete_float(state: TuiState, show: FilterOrBool) -> Float:
    """削除確認 modal の Float を組み立てる。"""
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
    modal.notice = None
    return True


def close_delete_modal(state: TuiState) -> None:
    """削除確認 modal を閉じて入力をクリアする。"""
    modal = state.issue_tab.delete_modal
    modal.show = False
    modal.input_text = ""
    modal.notice = None


def validate_input(modal: IssueDeleteModalState) -> str | None:
    """入力が対象の issue_id と一致しない理由を返す。一致していれば None。"""
    entered = modal.input_text.strip()
    if not entered:
        return messages.tui_issue_delete_modal_empty
    if entered != str(modal.target_id):
        return messages.tui_issue_delete_modal_mismatch
    return None


def apply_deleted(state: TuiState, issue_id: int) -> None:
    """削除済みの issue を一覧から取り除き、total_count と cursor を整える。"""
    issues = state.issue_tab.issues
    index = next(
        (i for i, issue in enumerate(issues) if issue.get("id") == issue_id),
        None,
    )
    if index is None:
        return
    issues.pop(index)
    state.issue_tab.total_count = max(0, state.issue_tab.total_count - 1)
    if state.issue_tab.cursor >= len(issues):
        state.issue_tab.cursor = max(0, len(issues) - 1)


def confirm_delete(state: TuiState) -> None:
    """modal で入力された issue_id が modal を開いた対象と一致したら削除する。

    入力が空の場合と一致しない場合は modal.notice に理由を出して再入力させる。
    削除成功時は modal を閉じ、ローカルの issue 一覧から該当行を取り除く。
    削除失敗時は modal を閉じて flash_message にエラーを出す。
    """
    modal = state.issue_tab.delete_modal
    notice = validate_input(modal)
    if notice is not None:
        modal.notice = notice
        return
    try:
        issue_service.delete_issue(str(modal.target_id))
    except IssueNotFoundException:
        close_delete_modal(state)
        state.flash_message = messages.tui_issue_delete_missing.format(
            id=modal.target_id
        )
        return
    except requests.exceptions.RequestException as e:
        close_delete_modal(state)
        state.flash_message = messages.tui_issue_delete_failed.format(error=e)
        return
    apply_deleted(state, modal.target_id)
    close_delete_modal(state)


def input_digit(state: TuiState, digit: str) -> None:
    """入力欄に数字を1文字追加する。"""
    modal = state.issue_tab.delete_modal
    modal.input_text += digit
    modal.notice = None


def backspace(state: TuiState) -> None:
    """入力欄の末尾を1文字削る。"""
    modal = state.issue_tab.delete_modal
    if modal.input_text:
        modal.input_text = modal.input_text[:-1]
        modal.notice = None
