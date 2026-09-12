"""issues タブの D で開く削除確認ダイアログのレイアウト・描画と、開く/閉じる/確定する操作。

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
from redi.tui.state import Renderable, TuiState
from redi.tui.state.issue_tab import IssueDeleteDialogState


def render_delete_dialog(state: TuiState) -> Renderable:
    dialog = state.issue_tab.delete_dialog
    parts: Renderable = []
    parts.append(
        (
            "",
            messages.tui_issue_delete_dialog_target.format(
                id=dialog.target_id, subject=dialog.target_subject
            )
            + "\n\n",
        )
    )
    parts.append(
        (
            "",
            messages.tui_issue_delete_dialog_prompt.format(expected=dialog.target_id)
            + "\n",
        )
    )
    parts.append(("bold fg:ansicyan", messages.tui_issue_delete_dialog_input_label))
    parts.append(("", dialog.input_text))
    # 末尾の反転した空白を入力カーソルに見立てる
    parts.append(("reverse", " "))
    parts.append(("", "\n"))
    if dialog.notice:
        parts.append(("fg:ansired", dialog.notice + "\n"))
    parts.append(("", "\n"))
    parts.append(("", messages.tui_issue_delete_dialog_hint))
    return parts


def build_delete_dialog(state: TuiState, show: FilterOrBool) -> Float:
    """削除確認ダイアログの Float を組み立てる。"""
    return Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        Window(
                            FormattedTextControl(
                                lambda: render_delete_dialog(state),
                                show_cursor=False,
                            ),
                            # 何を消すかが読めないと確認にならないので subject は折り返す
                            wrap_lines=True,
                        ),
                        title=lambda: messages.tui_issue_delete_dialog_title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=show,
        ),
    )


def open_delete_dialog(state: TuiState) -> bool:
    """カーソル位置の issue を対象に削除確認ダイアログを開く。対象がなければ False。"""
    issues = state.issue_tab.issues
    if not issues:
        return False
    issue = issues[state.issue_tab.cursor]
    issue_id = issue.get("id")
    if issue_id is None:
        return False
    dialog = state.issue_tab.delete_dialog
    dialog.show = True
    dialog.target_id = int(issue_id)
    dialog.target_subject = str(issue.get("subject", ""))
    dialog.input_text = ""
    dialog.notice = None
    return True


def close_delete_dialog(state: TuiState) -> None:
    """削除確認ダイアログを閉じて入力をクリアする。"""
    dialog = state.issue_tab.delete_dialog
    dialog.show = False
    dialog.input_text = ""
    dialog.notice = None


def validate_input(dialog: IssueDeleteDialogState) -> str | None:
    """入力が対象の issue_id と一致しない理由を返す。一致していれば None。"""
    entered = dialog.input_text.strip()
    if not entered:
        return messages.tui_issue_delete_dialog_empty
    if entered != str(dialog.target_id):
        return messages.tui_issue_delete_dialog_mismatch
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
    """ダイアログで入力された issue_id がダイアログを開いた対象と一致したら削除する。

    入力が空の場合と一致しない場合はダイアログ.notice に理由を出して再入力させる。
    削除成功時はダイアログを閉じ、ローカルの issue 一覧から該当行を取り除く。
    削除失敗時はダイアログを閉じて flash_message にエラーを出す。
    """
    dialog = state.issue_tab.delete_dialog
    notice = validate_input(dialog)
    if notice is not None:
        dialog.notice = notice
        return
    try:
        issue_service.delete_issue(str(dialog.target_id))
    except IssueNotFoundException:
        close_delete_dialog(state)
        state.flash_message = messages.tui_issue_delete_missing.format(
            id=dialog.target_id
        )
        return
    except requests.exceptions.RequestException as e:
        close_delete_dialog(state)
        state.flash_message = messages.tui_issue_delete_failed.format(error=e)
        return
    apply_deleted(state, dialog.target_id)
    close_delete_dialog(state)


def input_digit(state: TuiState, digit: str) -> None:
    """入力欄に数字を1文字追加する。"""
    dialog = state.issue_tab.delete_dialog
    dialog.input_text += digit
    dialog.notice = None


def backspace(state: TuiState) -> None:
    """入力欄の末尾を1文字削る。"""
    dialog = state.issue_tab.delete_dialog
    if dialog.input_text:
        dialog.input_text = dialog.input_text[:-1]
        dialog.notice = None
