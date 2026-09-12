"""wiki タブの h で開く版選択 modal と、選んだ版を表示する操作。

Redmine の REST API には wiki の版一覧を返すエンドポイントが無い。最新版の番号は
一覧 (`/wiki/index.json`) の `version` で分かるので、1..最新 を並べて選ばせる。
HTTP は `service.wiki_service` に任せ、ここでは状態の更新だけを行う。
"""

from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.layout.containers import Float

from redi.api.wiki import WikiPage
from redi.i18n import messages
from redi.tui.choice_dialog import build_choice_dialog
from redi.tui.state import TuiState
from redi.tui.state.wiki_tab import WikiVersionView
from redi.tui.wiki.wiki_tab import current_page, load_version_text, viewing_version


def build_version_dialog(state: TuiState, show: FilterOrBool) -> Float:
    return build_choice_dialog(
        lambda: state.wiki_tab.version_dialog,
        messages.tui_wiki_version_modal_title,
        messages.tui_wiki_version_modal_hint,
        show,
    )


def latest_version(page: WikiPage | None) -> int | None:
    """ページの最新版番号。ページが無いか版が不明なら None。"""
    if page is None:
        return None
    version = page.get("version")
    if not version:
        return None
    return int(version)


def version_label(version: int, latest: int) -> str:
    """版の表示ラベル。最新版には (最新) を添える。差分 modal の列でも使う。"""
    if version == latest:
        return messages.tui_wiki_version_latest_label.format(version=version)
    return messages.tui_wiki_version_label.format(version=version)


def open_version_dialog(state: TuiState) -> bool:
    """カーソル位置のページの版一覧 (最新が先頭) を出す。対象がなければ False。

    表示中の版に `*` を付け、カーソルもそこに置く。
    """
    latest = latest_version(current_page(state))
    if latest is None:
        return False
    dialog = state.wiki_tab.version_dialog
    dialog.choices = [(str(v), version_label(v, latest)) for v in range(latest, 0, -1)]
    view = viewing_version(state)
    current = view.version if view is not None else latest
    dialog.active_value = str(current)
    dialog.cursor = latest - current
    dialog.show = True
    return True


def select_version(state: TuiState, version: int) -> None:
    """カーソル位置のページの `version` を表示する。

    最新版を選んだら過去版の表示をやめて最新版に戻る。取得失敗は flash_message に
    出し、表示は変えない。差分を出していればそれも閉じる。
    """
    page = current_page(state)
    latest = latest_version(page)
    if page is None or latest is None:
        return
    title = page["title"]
    state.wiki_tab.diff_view = None
    if version == latest:
        state.wiki_tab.version_view = None
        return
    text = load_version_text(state, title, version, latest)
    if text is None:
        return
    state.wiki_tab.version_view = WikiVersionView(
        title=title, version=version, text=text, latest=latest
    )
