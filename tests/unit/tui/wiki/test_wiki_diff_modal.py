from typing import cast

import pytest

from redi.api.wiki import WikiPage
from redi.i18n import messages
from redi.service import wiki_service
from redi.tui.state import TuiState
from redi.tui.state.wiki_tab import WikiDiffColumn, WikiDiffView, WikiVersionView
from redi.tui.wiki import wiki_tab
from redi.tui.wiki.diff_modal import (
    apply_diff,
    clear_diff,
    move_cursor,
    move_cursor_to_end,
    open_diff_modal,
    render_diff_column,
)
from redi.tui.wiki.version_modal import select_version
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


def _column_text(state: TuiState, column: WikiDiffColumn) -> str:
    return "".join(t for _, t in render_diff_column(state, column))


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
        assert modal.versions[modal.cursors["from"]] == 2
        assert modal.versions[modal.cursors["to"]] == 3

    def test_from_is_viewing_version(self):
        """過去版を開いていれば 比較前 はその版から始まる"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.version_view = WikiVersionView("Home", 1, "a", latest=3)

        open_diff_modal(state)

        modal = state.wiki_tab.diff_modal
        assert modal.versions[modal.cursors["from"]] == 1
        assert modal.versions[modal.cursors["to"]] == 3

    def test_reopen_keeps_applied_pair(self):
        """差分を出しているときに開き直すと、その 2 版にカーソルが乗る"""
        state = _state([_page("Home", version=4)])
        state.wiki_tab.diff_view = WikiDiffView("Home", 3, 2, diff="")

        open_diff_modal(state)

        modal = state.wiki_tab.diff_modal
        assert modal.versions[modal.cursors["from"]] == 3
        assert modal.versions[modal.cursors["to"]] == 2

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

        from_col = _column_text(state, "from")
        to_col = _column_text(state, "to")

        assert ">   v2" in from_col
        assert ">" not in to_col
        assert "*" not in from_col + to_col

    def test_columns_mark_applied_pair(self):
        """差分を出していれば各列の適用中の版に * が付く"""
        state = _state([_page("Home", version=3)])
        state.wiki_tab.diff_view = WikiDiffView("Home", 1, 2, diff="")
        open_diff_modal(state)

        assert "* v1" in _column_text(state, "from")
        assert "* v2" in _column_text(state, "to")


class TestDiffModalCursor:
    """jk / gg / G は focus のある列だけを動かし、端で止まる"""

    def _modal(self):
        state = _state([_page("Home", version=3)])
        open_diff_modal(state)
        return state.wiki_tab.diff_modal

    def test_moves_focused_column_only(self):
        """j は focus のある列のカーソルだけ進める"""
        modal = self._modal()
        modal.focus = "to"

        move_cursor(modal, 1)

        assert modal.cursors == {"from": 1, "to": 1}

    def test_stops_at_edges(self):
        """先頭より上、末尾より下へは動かない"""
        modal = self._modal()

        move_cursor(modal, -5)
        assert modal.cursors["from"] == 0
        move_cursor(modal, 5)
        assert modal.cursors["from"] == 2

    def test_jump_to_top_and_bottom(self):
        """gg / G で先頭・末尾へ飛ぶ"""
        modal = self._modal()

        move_cursor_to_end(modal, top=False)
        assert modal.cursors["from"] == 2
        move_cursor_to_end(modal, top=True)
        assert modal.cursors["from"] == 0


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
        modal.cursors = {
            "from": modal.versions.index(from_version),
            "to": modal.versions.index(to_version),
        }

    def _applied(self, from_version: int, to_version: int) -> TuiState:
        """本文キャッシュ済みの状態で from → to の差分を適用した後の状態。"""
        state = self._state_with_texts()
        self._open_with(state, from_version, to_version)
        apply_diff(state)
        return state

    def test_apply_shows_diff_and_keeps_modal(self):
        """Enter で両列の版の差分を出す。フィルタと同じく modal は開いたまま"""
        state = self._state_with_texts()
        self._open_with(state, 2, 3)

        assert apply_diff(state) is True
        rendered = self._rendered(state)

        assert state.wiki_tab.diff_modal.show is True
        assert "--- v2" in rendered
        assert "+++ v3" in rendered
        assert "-b" in rendered
        assert "+B" in rendered

    def test_apply_keeps_chosen_direction(self):
        """比較前に新しい版、比較後に古い版を選べばその向きのまま出す"""
        state = self._applied(3, 2)

        rendered = self._rendered(state)

        assert "--- v3" in rendered
        assert "+++ v2" in rendered
        assert "-B" in rendered
        assert "+b" in rendered

    def test_apply_same_version_shows_no_changes(self):
        """同じ版どうしも弾かず、差分無しとして出す"""
        state = self._state_with_texts()
        self._open_with(state, 2, 2)

        assert apply_diff(state) is True

        assert state.wiki_tab.diff_view is not None
        assert state.wiki_tab.diff_view.diff == ""
        assert state.flash_message is None
        assert messages.tui_wiki_diff_no_changes in self._rendered(state)

    def test_apply_loads_missing_texts(self, monkeypatch):
        """本文が未取得なら適用時に取りに行き、キャッシュに載せる"""
        state = _state([_page("Home", version=3)])
        calls = _stub_read_page(monkeypatch, {None: "a\nB", 2: "a\nb"})
        self._open_with(state, 2, 3)

        apply_diff(state)

        assert calls == [2, None]
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
        state = self._applied(2, 3)

        styles = {
            text.rstrip("\n"): style for style, text in WIKI_TAB.render_preview(state)
        }

        assert styles["+B"] == "fg:ansigreen"
        assert styles["-b"] == "fg:ansired"

    def test_clear_returns_to_text(self):
        """c で差分をやめて本文に戻る。modal は開いたまま"""
        state = self._applied(2, 3)

        clear_diff(state)

        assert state.wiki_tab.diff_view is None
        assert state.wiki_tab.diff_modal.show is True
        assert "a\nB\nc" in self._rendered(state)

    def test_meta_shows_diff_versions(self):
        """差分表示中はメタ表の版が比較している 2 版と最新版になる"""
        state = self._applied(1, 2)

        assert messages.tui_wiki_meta_version_diff.format(
            from_version=1, to_version=2, latest=3
        ) in self._rendered(state)

    def test_status_hint_shows_diff(self):
        """差分表示中はステータスバーに 2 版を出す"""
        state = self._applied(2, 3)

        assert messages.tui_status_wiki_diff_active.format(
            from_version=2, to_version=3
        ) in WIKI_TAB.status_hint(state)

    def test_update_allowed_when_diff_on_latest(self):
        """最新版を見ながらの差分表示では u を止めない"""
        state = self._applied(2, 3)

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
        state = self._applied(1, 3)
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
        """h で版を選び直すと差分表示は閉じる"""
        state = self._applied(2, 3)

        select_version(state, 1)

        assert state.wiki_tab.diff_view is None
        assert viewing_version(state) == WikiVersionView("Home", 1, "a", latest=3)
