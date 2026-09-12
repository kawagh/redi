"""wiki タブの H で開く版選択 modal と、選んだ版を表示する操作。

Redmine の REST API には wiki の版一覧を返すエンドポイントが無い。最新版の番号は
一覧 (`/wiki/index.json`) の `version` で分かるので、1..最新 を並べて選ばせる。
HTTP は `service.wiki_service` に任せ、ここでは状態の更新だけを行う。
"""

import requests
from prompt_toolkit.filters import FilterOrBool
from prompt_toolkit.layout.containers import Float

from redi.api.wiki import WikiPage
from redi.i18n import messages
from redi.service import wiki_service
from redi.tui.choice_modal import build_choice_float
from redi.tui.state import TuiState, WikiVersionView
from redi.tui.wiki.wiki_tab import current_page, viewing_version


def build_version_float(state: TuiState, show: FilterOrBool) -> Float:
    return build_choice_float(
        lambda: state.wiki_tab.version_modal,
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


def open_version_modal(state: TuiState) -> bool:
    """カーソル位置のページの版一覧 (最新が先頭) を出す。対象がなければ False。

    表示中の版に `*` を付け、カーソルもそこに置く。
    """
    latest = latest_version(current_page(state))
    if latest is None:
        return False
    modal = state.wiki_tab.version_modal
    modal.choices = [
        (
            str(v),
            messages.tui_wiki_version_latest_label.format(version=v)
            if v == latest
            else messages.tui_wiki_version_label.format(version=v),
        )
        for v in range(latest, 0, -1)
    ]
    view = viewing_version(state)
    current = view.version if view is not None else latest
    modal.active_value = str(current)
    modal.cursor = latest - current
    modal.show = True
    return True


def select_version(state: TuiState, version: int) -> None:
    """カーソル位置のページの `version` を表示する。

    最新版を選んだら過去版の表示をやめて最新版に戻る。取得失敗は flash_message に
    出し、表示は変えない。
    """
    page = current_page(state)
    latest = latest_version(page)
    if page is None or latest is None:
        return
    title = page["title"]
    if version == latest:
        state.wiki_tab.version_view = None
        return
    text = state.wiki_tab.version_texts.get((title, version))
    if text is None:
        project = state.effective_wiki_project_id()
        if not project:
            state.flash_message = messages.tui_wiki_project_required
            return
        try:
            wiki = wiki_service.read_page(project, title, version=version)
        except requests.exceptions.RequestException as e:
            state.flash_message = messages.tui_wiki_version_load_failed.format(
                version=version, error=e
            )
            return
        if wiki is None:
            state.flash_message = messages.tui_wiki_version_missing.format(
                title=title, version=version
            )
            return
        text = wiki.get("text", "") or ""
        state.wiki_tab.version_texts[(title, version)] = text
    state.wiki_tab.version_view = WikiVersionView(
        title=title, version=version, text=text, latest=latest
    )
