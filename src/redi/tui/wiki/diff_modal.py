"""wiki タブの d で開く比較相手の版を選ぶ modal と、選んだ 2 版の差分を表示する操作。

基準は表示中の版 (過去版を開いていなければ最新版) で、選んだ版との差分を右ペインに出す。
Redmine の REST API には差分を返すエンドポイントが無いので、本文は
`wiki_tab.load_version_text` で取り、差分は `service.wiki_service.diff_texts` で手元で作る。
"""

from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.layout.containers import Float

from redi.i18n import messages
from redi.tui.choice_modal import build_choice_float
from redi.tui.state import TuiState, WikiDiffView
from redi.tui.wiki.version_modal import latest_version
from redi.tui.wiki.wiki_tab import (
    current_page,
    load_version_text,
    viewing_diff,
    viewing_version,
)


def build_diff_float(state: TuiState, show: FilterOrBool) -> Float:
    return build_choice_float(
        lambda: state.wiki_tab.diff_modal,
        messages.tui_wiki_diff_modal_title,
        messages.tui_wiki_diff_modal_hint,
        show,
    )


def base_version(state: TuiState) -> int | None:
    """差分の基準にする版。過去版を開いていればその版、そうでなければ最新版。"""
    view = viewing_version(state)
    if view is not None:
        return view.version
    return latest_version(current_page(state))


def toggle_diff(state: TuiState) -> bool:
    """差分を表示中なら閉じ、そうでなければ比較相手を選ぶ modal を開く。

    modal には基準以外の版を最新から順に並べ、カーソルは基準の 1 つ前の版に置く。
    Enter だけで「直前の版との差分」になる。版が 1 つしか無ければ flash で知らせる。
    """
    if viewing_diff(state) is not None:
        state.wiki_tab.diff_view = None
        return True
    latest = latest_version(current_page(state))
    base = base_version(state)
    if latest is None or base is None:
        return False
    if latest < 2:
        state.flash_message = messages.tui_wiki_diff_no_other_versions
        return False
    others = [v for v in range(latest, 0, -1) if v != base]
    modal = state.wiki_tab.diff_modal
    modal.choices = [
        (
            str(v),
            messages.tui_wiki_version_latest_label.format(version=v)
            if v == latest
            else messages.tui_wiki_version_label.format(version=v),
        )
        for v in others
    ]
    modal.active_value = None
    previous = base - 1 if base > 1 else others[-1]
    modal.cursor = others.index(previous)
    modal.show = True
    return True


def select_diff_target(state: TuiState, other: int) -> None:
    """基準の版と `other` の差分を表示する。番号の小さいほうを from にする。

    本文はここでキャッシュに載せ、取得に失敗したら表示は変えない (flash は取得側が出す)。
    """
    page = current_page(state)
    latest = latest_version(page)
    base = base_version(state)
    if page is None or latest is None or base is None or other == base:
        return
    title = page["title"]
    from_version, to_version = sorted((base, other))
    if load_version_text(state, title, from_version, latest) is None:
        return
    if load_version_text(state, title, to_version, latest) is None:
        return
    state.wiki_tab.diff_view = WikiDiffView(
        title=title, from_version=from_version, to_version=to_version
    )
