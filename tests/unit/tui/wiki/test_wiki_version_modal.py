from typing import cast

import pytest
import requests

from redi.api.wiki import WikiPage
from redi.i18n import messages
from redi.service import wiki_service
from redi.tui.state import TuiState, WikiDiffView, WikiVersionView
from redi.tui.wiki import version_modal, wiki_tab
from redi.tui.wiki.delete_modal import open_delete_modal
from redi.tui.wiki.diff_modal import (
    apply_diff,
    clear_diff,
    open_diff_modal,
    render_diff_column,
)
from redi.tui.wiki.version_modal import open_version_modal, select_version
from redi.tui.wiki.wiki_tab import WIKI_TAB, set_pages, viewing_diff, viewing_version


def _page(title: str, version: int = 1) -> WikiPage:
    return cast(WikiPage, {"title": title, "version": version})


def _state(pages: list[WikiPage], *, cursor: int = 0) -> TuiState:
    state = TuiState()
    state.tab = "wiki"
    set_pages(state, pages)
    state.wiki_tab.cursor = cursor
    return state


def _stub_read_page(monkeypatch, texts: dict[int | None, str]):
    """`read_page` を版番号 -> 本文 の辞書で差し替え、呼び出し回数を数える。"""
    calls: list[int | None] = []

    def fake(project_id, title, version=None, full=False):
        calls.append(version)
        if version not in texts:
            return None
        return cast(
            WikiPage, {"title": title, "version": version, "text": texts[version]}
        )

    monkeypatch.setattr(wiki_service, "read_page", fake)
    return calls


@pytest.fixture(autouse=True)
def _wiki_project(monkeypatch):
    monkeypatch.setattr("redi.config.wiki_project_id", "research")


class TestOpenVersionModal:
    """open_version_modal() は 1..最新 の版を最新から順に並べる"""

    def test_lists_versions_latest_first(self):
        """最新版が先頭で、最新版には (latest) の印が付く"""
        state = _state([_page("Home", version=3)])

        assert open_version_modal(state) is True

        modal = state.wiki_tab.version_modal
        assert modal.show is True
        assert [v for v, _ in modal.choices] == ["3", "2", "1"]
        assert modal.choices[0][1] == messages.tui_wiki_version_latest_label.format(
            version=3
        )
        assert modal.choices[1][1] == messages.tui_wiki_version_label.format(version=2)

    def test_marks_latest_when_viewing_latest(self):
        """最新版を表示中なら先頭が現在の版としてカーソル位置になる"""
        state = _state([_page("Home", version=3)])

        open_version_modal(state)

        assert state.wiki_tab.version_modal.active_value == "3"
        assert state.wiki_tab.version_modal.cursor == 0

    def test_marks_viewing_version(self):
        """過去版を表示中なら、その版にカーソルと現在の印を置く"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "old", latest=3)

        open_version_modal(state)

        assert state.wiki_tab.version_modal.active_value == "1"
        assert state.wiki_tab.version_modal.cursor == 2

    def test_returns_false_when_empty(self):
        """ページが無いときは modal を開かず False"""
        state = _state([])

        assert open_version_modal(state) is False
        assert state.wiki_tab.version_modal.show is False


class TestSelectVersion:
    """select_version() は選んだ版の本文を取得して表示状態にする"""

    def test_shows_selected_version(self, monkeypatch):
        """過去版を選ぶとその本文が version_view に入る"""
        state = _state([_page("Home", version=3)])
        _stub_read_page(monkeypatch, {1: "first"})

        select_version(state, 1)

        assert viewing_version(state) == WikiVersionView("Home", 1, "first", latest=3)

    def test_latest_returns_to_latest(self, monkeypatch):
        """最新版を選ぶと過去版の表示をやめる (API は呼ばない)"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "first", latest=3)
        calls = _stub_read_page(monkeypatch, {})

        select_version(state, 3)

        assert state.wiki_tab.version_view is None
        assert calls == []

    def test_reuses_cached_text(self, monkeypatch):
        """同じ版を再び選んでも取得し直さない (過去版は変わらない)"""
        state = _state([_page("Home", version=3)])
        calls = _stub_read_page(monkeypatch, {1: "first"})

        select_version(state, 1)
        select_version(state, 3)
        select_version(state, 1)

        assert calls == [1]

    def test_missing_version_flashes(self, monkeypatch):
        """Redmine に無い版 (404) は flash で知らせる"""
        state = _state([_page("Home", version=3)])
        _stub_read_page(monkeypatch, {})

        select_version(state, 2)

        assert state.wiki_tab.version_view is None
        assert state.flash_message == messages.tui_wiki_version_missing.format(
            title="Home", version=2
        )

    def test_request_error_flashes(self, monkeypatch):
        """取得に失敗したら flash で知らせて表示を変えない"""
        state = _state([_page("Home", version=3)])

        def fail(*args, **kwargs):
            raise requests.exceptions.ConnectionError("boom")

        monkeypatch.setattr(wiki_service, "read_page", fail)

        select_version(state, 2)

        assert state.wiki_tab.version_view is None
        assert state.flash_message is not None
        assert "boom" in state.flash_message


class TestViewResetsOnMove:
    """過去版の表示はページ単位で、別ページへ移ると最新版に戻る"""

    def test_moving_cursor_returns_to_latest(self):
        """カーソルを別ページへ動かすと過去版の表示をやめる"""
        state = _state([_page("Guide", version=2), _page("Home", version=3)])
        state.wiki_tab.version_view = WikiVersionView("Guide", 1, "old", latest=2)

        WIKI_TAB.on_down(state)

        assert state.wiki_tab.version_view is None

    def test_staying_keeps_view(self):
        """末尾で j を押してもカーソルが動かなければ表示は保つ"""
        state = _state([_page("Guide", version=2), _page("Home", version=3)], cursor=1)
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "old", latest=3)

        WIKI_TAB.on_down(state)

        assert viewing_version(state) is not None

    def test_view_for_other_page_is_ignored(self):
        """version_view のタイトルがカーソル位置と違えば最新版扱いにする"""
        state = _state([_page("Guide", version=2), _page("Home", version=3)], cursor=1)
        state.wiki_tab.version_view = WikiVersionView("Guide", 1, "old", latest=2)

        assert viewing_version(state) is None

    def test_reload_clears_view_and_cache(self, monkeypatch):
        """R で取り直すと過去版の表示とキャッシュを捨てる"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "old", latest=3)
        state.wiki_tab.version_texts[("Home", 1)] = "old"
        monkeypatch.setattr(wiki_service, "list_pages", lambda project: [])

        WIKI_TAB.on_reload(state)

        assert state.wiki_tab.version_view is None
        assert state.wiki_tab.version_texts == {}


class TestReadOnlyWhileViewingOldVersion:
    """過去版を表示中は更新・削除に進ませない"""

    def test_update_is_blocked(self):
        """u を押しても TUI を抜けず、flash で最新版に戻るよう促す"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "old", latest=3)

        assert WIKI_TAB.on_action_key(state, "u") is None
        assert state.flash_message == messages.tui_wiki_version_readonly

    def test_update_allowed_on_latest(self):
        """最新版に戻れば u で更新に進める"""
        state = _state([_page("Home", version=3)])

        result = WIKI_TAB.on_action_key(state, "u")

        assert result is not None
        assert result.action == "update"

    def test_delete_modal_is_blocked(self):
        """D を押しても削除確認 modal を開かず、flash で最新版に戻るよう促す"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "old", latest=3)

        assert open_delete_modal(state) is False
        assert state.wiki_tab.delete_modal.show is False
        assert state.flash_message == messages.tui_wiki_version_readonly

    def test_create_child_is_allowed(self):
        """子ページの作成は既存の本文を触らないので過去版表示中でも進める"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "old", latest=3)

        result = WIKI_TAB.on_action_key(state, "c")

        assert result is not None
        assert result.action == "create"


class TestIndication:
    """過去版を表示中であることが画面で分かる"""

    def test_preview_shows_old_text_and_versions(self):
        """プレビューは過去版の本文を出し、メタ表に表示中の版と最新版を併記する"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.texts["Home"] = "latest body"
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "old body", latest=3)

        rendered = "".join(text for _, text in WIKI_TAB.render_preview(state))

        assert "old body" in rendered
        assert "latest body" not in rendered
        assert (
            messages.tui_wiki_meta_version_of_latest.format(version=1, latest=3)
            in rendered
        )

    def test_status_hint_shows_version(self):
        """ステータスバーに表示中の版と最新版を出す"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "old", latest=3)

        hint = WIKI_TAB.status_hint(state)

        assert (
            messages.tui_status_wiki_version_active.format(version=1, latest=3) in hint
        )

    def test_status_hint_plain_on_latest(self):
        """最新版のときは版の印を出さない"""
        state = _state([_page("Home", version=3)])

        assert WIKI_TAB.status_hint(state) == messages.tui_status_hint_wiki

    def test_open_web_uses_version(self, monkeypatch):
        """v は表示中の版の URL を開く"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "old", latest=3)
        opened: list[str] = []
        monkeypatch.setattr(wiki_tab.webbrowser, "open", opened.append)
        monkeypatch.setattr("redi.config.redmine_url", "http://redmine.example")

        WIKI_TAB.on_open_web(state)

        assert opened == ["http://redmine.example/projects/research/wiki/Home/1"]


class TestVersionModalModule:
    """version_modal は wiki タブの最新版番号を一覧の version から取る"""

    def test_latest_version_none_without_version(self):
        """一覧に version が無ければ最新版は不明 (None)"""
        state = _state([cast(WikiPage, {"title": "Home"})])

        assert version_modal.latest_version(wiki_tab.current_page(state)) is None
        assert open_version_modal(state) is False


class TestDiffModal:
    """d で開く modal は比較前と比較後を 2 列で選び、開いた時点で妥当な組が入っている"""

    def test_from_is_previous_and_to_is_latest_when_viewing_latest(self):
        """最新版を見ながらの d は 比較前=1 つ前の版、比較後=最新版 から始まる"""
        state = _state([_page("Home", version=3)])

        assert open_diff_modal(state) is True

        modal = state.wiki_tab.diff_modal
        assert modal.show is True
        assert modal.focus == "from"
        assert modal.versions == [3, 2, 1]
        assert modal.versions[modal.from_cursor] == 2
        assert modal.versions[modal.to_cursor] == 3

    def test_from_is_viewing_version(self):
        """過去版を開いていれば 比較前 はその版から始まる"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "a", latest=3)

        open_diff_modal(state)

        modal = state.wiki_tab.diff_modal
        assert modal.versions[modal.from_cursor] == 1
        assert modal.versions[modal.to_cursor] == 3

    def test_reopen_keeps_applied_pair(self):
        """差分を出しているときに開き直すと、その 2 版にカーソルが乗る"""
        state = _state([_page("Home", version=4)])
        state.wiki_tab.diff_view = WikiDiffView("Home", 3, 2)

        open_diff_modal(state)

        modal = state.wiki_tab.diff_modal
        assert modal.versions[modal.from_cursor] == 3
        assert modal.versions[modal.to_cursor] == 2

    def test_single_version_flashes(self):
        """版が 1 つしか無ければ modal を開かず flash で知らせる"""
        state = _state([_page("Home", version=1)])

        assert open_diff_modal(state) is False
        assert state.wiki_tab.diff_modal.show is False
        assert state.flash_message == messages.tui_wiki_diff_no_other_versions

    def test_cursor_only_in_focused_column(self):
        """カーソル行を出すのは focus のある列だけ。* は適用前は付かない"""
        state = _state([_page("Home", version=3)])
        open_diff_modal(state)

        from_col = "".join(t for _, t in render_diff_column(state, "from"))
        to_col = "".join(t for _, t in render_diff_column(state, "to"))

        assert ">   v2" in from_col
        assert ">" not in to_col
        assert "*" not in from_col + to_col

    def test_columns_mark_applied_pair(self):
        """差分を出していれば各列の適用中の版に * が付く"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.diff_view = WikiDiffView("Home", 1, 2)
        open_diff_modal(state)

        from_col = "".join(t for _, t in render_diff_column(state, "from"))
        to_col = "".join(t for _, t in render_diff_column(state, "to"))

        assert "* v1" in from_col
        assert "* v2" in to_col


class TestDiff:
    """modal で選んだ 2 版の差分を右ペインで見られる"""

    def _rendered(self, state: TuiState) -> str:
        return "".join(text for _, text in WIKI_TAB.render_preview(state))

    def _state_with_texts(self) -> TuiState:
        state = _state([_page("Home", version=3)])
        state.wiki_tab.texts["Home"] = "a\nB\nc"
        state.wiki_tab.version_texts[("Home", 2)] = "a\nb\nc"
        state.wiki_tab.version_texts[("Home", 1)] = "a"
        return state

    def _open_with(self, state: TuiState, from_version: int, to_version: int) -> None:
        open_diff_modal(state)
        modal = state.wiki_tab.diff_modal
        modal.from_cursor = modal.versions.index(from_version)
        modal.to_cursor = modal.versions.index(to_version)

    def test_apply_shows_diff_and_keeps_modal(self):
        """Enter で両列の版の差分を出す。フィルタと同じく modal は開いたまま"""
        state = self._state_with_texts()
        self._open_with(state, 2, 3)

        assert apply_diff(state) is True
        rendered = self._rendered(state)

        assert state.wiki_tab.diff_modal.show is True
        assert state.wiki_tab.diff_view == WikiDiffView("Home", 2, 3)
        assert "--- v2" in rendered
        assert "+++ v3" in rendered
        assert "-b" in rendered
        assert "+B" in rendered

    def test_apply_keeps_chosen_direction(self):
        """比較前に新しい版、比較後に古い版を選べばその向きのまま出す"""
        state = self._state_with_texts()
        self._open_with(state, 3, 2)

        apply_diff(state)
        rendered = self._rendered(state)

        assert state.wiki_tab.diff_view == WikiDiffView("Home", 3, 2)
        assert "--- v3" in rendered
        assert "+++ v2" in rendered
        assert "-B" in rendered
        assert "+b" in rendered

    def test_apply_same_version_keeps_modal(self):
        """同じ版どうしは flash で知らせ、modal は開いたまま"""
        state = self._state_with_texts()
        self._open_with(state, 2, 2)

        assert apply_diff(state) is False

        assert state.wiki_tab.diff_modal.show is True
        assert state.wiki_tab.diff_view is None
        assert state.flash_message == messages.tui_wiki_diff_same_version

    def test_apply_loads_missing_texts(self, monkeypatch):
        """本文が未取得なら適用時に取りに行き、キャッシュに載せる"""
        state = _state([_page("Home", version=3)])
        calls = _stub_read_page(monkeypatch, {None: "a\nB", 2: "a\nb"})
        self._open_with(state, 2, 3)

        apply_diff(state)

        assert sorted(calls, key=str) == [2, None]
        assert state.wiki_tab.texts["Home"] == "a\nB"
        assert state.wiki_tab.version_texts[("Home", 2)] == "a\nb"
        assert "+B" in self._rendered(state)

    def test_apply_failure_keeps_text_view(self, monkeypatch):
        """本文が取れなければ差分に切り替えず、flash で知らせる"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.texts["Home"] = "latest"
        _stub_read_page(monkeypatch, {})
        self._open_with(state, 2, 3)

        assert apply_diff(state) is False
        assert state.wiki_tab.diff_view is None
        assert state.flash_message == messages.tui_wiki_version_missing.format(
            title="Home", version=2
        )
        assert "latest" in self._rendered(state)

    def test_diff_lines_are_styled(self):
        """追加行と削除行に色が付く"""
        state = self._state_with_texts()
        self._open_with(state, 2, 3)
        apply_diff(state)

        styles = {
            text.rstrip("\n"): style for style, text in WIKI_TAB.render_preview(state)
        }

        assert styles["+B"] == "fg:ansigreen"
        assert styles["-b"] == "fg:ansired"

    def test_no_changes_message(self):
        """差分が無ければその旨を出す"""
        state = self._state_with_texts()
        state.wiki_tab.version_texts[("Home", 2)] = "a\nB\nc"
        self._open_with(state, 2, 3)
        apply_diff(state)

        assert messages.tui_wiki_diff_no_changes in self._rendered(state)

    def test_clear_returns_to_text(self):
        """c で差分をやめて本文に戻る。modal は開いたまま"""
        state = self._state_with_texts()
        self._open_with(state, 2, 3)
        apply_diff(state)

        clear_diff(state)

        assert state.wiki_tab.diff_view is None
        assert state.wiki_tab.diff_modal.show is True
        assert "a\nB\nc" in self._rendered(state)

    def test_status_hint_shows_diff(self):
        """差分表示中はステータスバーに 2 版を出す"""
        state = self._state_with_texts()
        self._open_with(state, 2, 3)
        apply_diff(state)

        assert messages.tui_status_wiki_diff_active.format(
            from_version=2, to_version=3
        ) in WIKI_TAB.status_hint(state)

    def test_update_allowed_when_diff_on_latest(self):
        """最新版を見ながらの差分表示では u を止めない"""
        state = self._state_with_texts()
        self._open_with(state, 2, 3)
        apply_diff(state)

        assert WIKI_TAB.on_action_key(state, "u") is not None

    def test_update_stays_blocked_when_viewing_old(self):
        """過去版を開いたままの差分表示では u を止めたまま"""
        state = self._state_with_texts()
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "a", latest=3)
        self._open_with(state, 1, 3)
        apply_diff(state)

        assert WIKI_TAB.on_action_key(state, "u") is None
        assert state.flash_message == messages.tui_wiki_version_readonly

    def test_open_web_uses_diff_url(self, monkeypatch):
        """差分表示中の v は Redmine の差分画面を開く"""
        state = self._state_with_texts()
        self._open_with(state, 1, 3)
        apply_diff(state)
        opened: list[str] = []
        monkeypatch.setattr(wiki_tab.webbrowser, "open", opened.append)
        monkeypatch.setattr("redi.config.redmine_url", "http://redmine.example")

        WIKI_TAB.on_open_web(state)

        assert opened == [
            "http://redmine.example/projects/research/wiki/Home/diff?version=3&version_from=1"
        ]

    def test_moving_cursor_clears_diff(self):
        """別ページへ移ると差分表示も解除される"""
        state = _state([_page("Guide", version=2), _page("Home", version=3)], cursor=1)
        state.wiki_tab.texts["Home"] = "x"
        state.wiki_tab.version_texts[("Home", 2)] = "y"
        self._open_with(state, 2, 3)
        apply_diff(state)

        WIKI_TAB.on_up(state)

        assert viewing_diff(state) is None

    def test_selecting_version_closes_diff(self):
        """H で版を選び直すと差分表示は閉じる"""
        state = self._state_with_texts()
        self._open_with(state, 2, 3)
        apply_diff(state)

        select_version(state, 1)

        assert state.wiki_tab.diff_view is None
        assert viewing_version(state) == WikiVersionView("Home", 1, "a", latest=3)
