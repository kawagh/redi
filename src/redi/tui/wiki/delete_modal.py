"""wiki タブの D で開く削除確認 modal のレイアウト・描画と、開く/閉じる/確定する操作。

wiki は issue_id にあたる数値 id を持たないため、確認語 (`delete`) を打たせて確定する。
HTTP は `service.wiki_service` に任せ、ここでは入力の検証と状態の更新だけを行う。
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

from redi.api.wiki import WikiPage
from redi.i18n import messages
from redi.service import wiki_service
from redi.tui.state import Renderable, TuiState, WikiDeleteModalState
from redi.tui.wiki.wiki_tab import set_pages

# 削除を確定するために打たせる語。ASCII 固定なので日本語タイトルでも入力できる。
CONFIRM_WORD = "delete"


def render_delete_modal(state: TuiState) -> Renderable:
    modal = state.wiki_tab.delete_modal
    parts: Renderable = []
    parts.append(
        ("", messages.tui_wiki_delete_modal_target.format(title=modal.target_title))
    )
    parts.append(("", "\n"))
    parts.append(("fg:ansiyellow", messages.tui_wiki_delete_modal_warning))
    parts.append(("", "\n\n"))
    parts.append(
        ("", messages.tui_wiki_delete_modal_prompt.format(expected=CONFIRM_WORD) + "\n")
    )
    parts.append(("bold fg:ansicyan", messages.tui_wiki_delete_modal_input_label))
    parts.append(("", modal.input_text))
    # 末尾の反転した空白を入力カーソルに見立てる
    parts.append(("reverse", " "))
    parts.append(("", "\n"))
    if modal.notice:
        parts.append(("fg:ansired", modal.notice + "\n"))
    parts.append(("", "\n"))
    parts.append(("", messages.tui_wiki_delete_modal_hint))
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
                            # 何を消すかが読めないと確認にならないので title は折り返す
                            wrap_lines=True,
                        ),
                        title=lambda: messages.tui_wiki_delete_modal_title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=show,
        ),
    )


def open_delete_modal(state: TuiState) -> bool:
    """カーソル位置の wiki ページを対象に削除確認 modal を開く。対象がなければ False。"""
    pages = state.wiki_tab.pages
    if not pages:
        return False
    title = pages[state.wiki_tab.cursor].get("title")
    if not title:
        return False
    modal = state.wiki_tab.delete_modal
    modal.show = True
    modal.target_title = title
    modal.input_text = ""
    modal.notice = None
    return True


def close_delete_modal(state: TuiState) -> None:
    """削除確認 modal を閉じて入力をクリアする。"""
    modal = state.wiki_tab.delete_modal
    modal.show = False
    modal.input_text = ""
    modal.notice = None


def validate_input(modal: WikiDeleteModalState) -> str | None:
    """入力が確認語と一致しない理由を返す。一致していれば None。"""
    entered = modal.input_text.strip()
    if not entered:
        return messages.tui_wiki_delete_modal_empty.format(expected=CONFIRM_WORD)
    if entered != CONFIRM_WORD:
        return messages.tui_wiki_delete_modal_mismatch.format(expected=CONFIRM_WORD)
    return None


def apply_deleted(state: TuiState, page_title: str) -> None:
    """削除済みのページを一覧から取り除き、cursor を範囲内に戻す。

    Redmine は削除したページの子ページを消さず、親を外して最上位に繰り上げるため、
    一覧のツリーも同じ形になるよう子ページの parent を落とす。
    """
    remaining: list[WikiPage] = []
    for page in state.wiki_tab.pages:
        if page.get("title") == page_title:
            continue
        parent = page.get("parent")
        if parent is not None and parent["title"] == page_title:
            del page["parent"]
        remaining.append(page)
    set_pages(state, remaining)
    state.wiki_tab.texts.pop(page_title, None)
    if state.wiki_tab.cursor >= len(state.wiki_tab.pages):
        state.wiki_tab.cursor = max(0, len(state.wiki_tab.pages) - 1)


def confirm_delete(state: TuiState) -> None:
    """modal で入力された確認語が一致したら対象ページを削除する。

    一致しない場合は modal.notice に理由を出して再入力させる。
    削除成功時は modal を閉じ、ローカルの一覧から対象ページを取り除く。
    削除失敗時は modal を閉じて flash_message にエラーを出す。
    """
    modal = state.wiki_tab.delete_modal
    notice = validate_input(modal)
    if notice is not None:
        modal.notice = notice
        return
    project = state.effective_wiki_project_id()
    if not project:
        close_delete_modal(state)
        state.flash_message = messages.tui_wiki_project_required
        return
    try:
        wiki_service.delete_page(project, modal.target_title)
    except wiki_service.WikiPageNotFoundError:
        close_delete_modal(state)
        state.flash_message = messages.tui_wiki_delete_page_missing.format(
            title=modal.target_title
        )
        return
    except requests.exceptions.RequestException as e:
        close_delete_modal(state)
        state.flash_message = messages.tui_wiki_delete_failed.format(error=e)
        return
    apply_deleted(state, modal.target_title)
    close_delete_modal(state)


def input_char(state: TuiState, char: str) -> None:
    """入力欄に1文字追加する。"""
    modal = state.wiki_tab.delete_modal
    modal.input_text += char
    modal.notice = None


def backspace(state: TuiState) -> None:
    """入力欄の末尾を1文字削る。"""
    modal = state.wiki_tab.delete_modal
    if modal.input_text:
        modal.input_text = modal.input_text[:-1]
        modal.notice = None
