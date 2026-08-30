"""issue タブの F で開く検索 modal のレイアウト・描画と、開く/閉じる/確定する操作。

`/` のバッファ内検索と違い、Redmine の検索 API を叩いてイシュー一覧そのものを
置き換える。HTTP は `service.search_service` に任せ、ここでは入力と状態だけを扱う。
"""

import re

from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame

from redi.i18n import messages
from redi.tui.issue.issue_tab import reload_with_filter
from redi.tui.state import Renderable, TuiState

# 末尾の1単語。全角スペースも Unicode の空白として区切りに使える
_TRAILING_WORD = re.compile(r"\S+$")


def render_find_modal(state: TuiState) -> Renderable:
    modal = state.issue_tab.find_modal
    parts: Renderable = []
    parts.append(("bold fg:ansicyan", messages.tui_find_modal_input_label))
    parts.append(("", modal.input_text))
    # 末尾の反転した空白を入力カーソルに見立てる
    parts.append(("reverse", " "))
    parts.append(("", "\n\n"))
    parts.append(("", messages.tui_find_modal_hint))
    return parts


def build_find_float(state: TuiState, show: FilterOrBool) -> Float:
    """検索 modal の Float を組み立てる。"""
    return Float(
        content=ConditionalContainer(
            content=VSplit(
                [
                    Window(width=1, char=" "),
                    Frame(
                        Window(
                            FormattedTextControl(
                                lambda: render_find_modal(state),
                                show_cursor=False,
                            ),
                            wrap_lines=True,
                        ),
                        title=lambda: messages.tui_find_modal_title,
                    ),
                    Window(width=1, char=" "),
                ]
            ),
            filter=show,
        ),
    )


def open_find_modal(state: TuiState) -> None:
    """検索 modal を開く。直前のクエリで初期化して打ち直しを省く。"""
    modal = state.issue_tab.find_modal
    modal.show = True
    modal.input_text = state.issue_tab.find.query


def close_find_modal(state: TuiState) -> None:
    """検索 modal を閉じて入力をクリアする。"""
    modal = state.issue_tab.find_modal
    modal.show = False
    modal.input_text = ""


def confirm_find(state: TuiState) -> None:
    """入力されたクエリで検索し直す。空のまま確定したら検索を解除する。"""
    state.issue_tab.find.query = state.issue_tab.find_modal.input_text.strip()
    reload_with_filter(state)
    close_find_modal(state)


def input_char(state: TuiState, char: str) -> None:
    state.issue_tab.find_modal.input_text += char


def backspace(state: TuiState) -> None:
    modal = state.issue_tab.find_modal
    modal.input_text = modal.input_text[:-1]


def delete_word(state: TuiState) -> None:
    """末尾の1単語を消す。カーソルは常に末尾なので後ろから削るだけでよい。"""
    modal = state.issue_tab.find_modal
    modal.input_text = _TRAILING_WORD.sub("", modal.input_text.rstrip())


def clear_input(state: TuiState) -> None:
    state.issue_tab.find_modal.input_text = ""
