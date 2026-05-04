"""TUI タブの再読込 (R キー) 挙動の単体テスト。"""

import pytest

from redi.tui import issue_tab, time_entry_tab, wiki_tab
from redi.tui.state import TuiState


class TestIssueReload:
    """issue タブの _on_reload() は現在のページを再取得する"""

    def test_preserves_offset_and_cursor_within_bounds(self, monkeypatch):
        """再取得後も offset は変えず、cursor は新しい一覧の範囲内に保たれる"""
        state = TuiState()
        state.page_size = 5
        state.issue_tab.offset = 10
        state.issue_tab.cursor = 2
        state.issue_tab.issues = [
            {"id": i, "subject": f"old-{i}"} for i in range(11, 16)
        ]
        state.issue_tab.total_count = 30

        new_issues = [{"id": i, "subject": f"new-{i}"} for i in range(11, 16)]

        def fake_fetch(state, offset):
            assert offset == 10
            return {"issues": new_issues, "total_count": 30}

        monkeypatch.setattr(issue_tab, "fetch_issues_with_filter", fake_fetch)

        issue_tab._on_reload(state)

        assert state.issue_tab.offset == 10
        assert state.issue_tab.cursor == 2
        assert state.issue_tab.issues == new_issues
        assert state.issue_tab.total_count == 30

    def test_clamps_cursor_when_new_page_is_shorter(self, monkeypatch):
        """再取得結果の件数が減ったら cursor は末尾にクランプされる"""
        state = TuiState()
        state.page_size = 5
        state.issue_tab.offset = 0
        state.issue_tab.cursor = 4
        state.issue_tab.issues = [{"id": i, "subject": f"old-{i}"} for i in range(1, 6)]
        state.issue_tab.total_count = 5

        new_issues = [{"id": 1, "subject": "only"}]
        monkeypatch.setattr(
            issue_tab,
            "fetch_issues_with_filter",
            lambda state, offset: {"issues": new_issues, "total_count": 1},
        )

        issue_tab._on_reload(state)

        assert state.issue_tab.cursor == 0
        assert state.issue_tab.issues == new_issues

    def test_empty_result_resets_cursor(self, monkeypatch):
        """再取得結果が空でも例外を投げず cursor=0 になる"""
        state = TuiState()
        state.page_size = 5
        state.issue_tab.cursor = 3
        state.issue_tab.issues = [{"id": 1, "subject": "x"}]
        monkeypatch.setattr(
            issue_tab,
            "fetch_issues_with_filter",
            lambda state, offset: {"issues": [], "total_count": 0},
        )

        issue_tab._on_reload(state)

        assert state.issue_tab.cursor == 0
        assert state.issue_tab.issues == []
        assert state.issue_tab.total_count == 0


class TestWikiReload:
    """wiki タブの _on_reload() は loaded を倒して取り直す"""

    def test_resets_loaded_and_restores_cursor_by_title(self, monkeypatch):
        """同じタイトルが残っていれば cursor をその位置に復元する"""
        state = TuiState()
        state.wiki_tab.loaded = True
        state.wiki_tab.pages = [
            {"title": "A"},
            {"title": "B"},
            {"title": "C"},
        ]
        state.wiki_tab.labels = ["A", "B", "C"]
        state.wiki_tab.cursor = 1  # B にいる
        state.wiki_tab.texts = {"A": "cached"}

        def fake_load(state):
            # loaded フラグが下りた状態で呼ばれること
            assert state.wiki_tab.loaded is False
            state.wiki_tab.loaded = True
            state.wiki_tab.pages = [
                {"title": "Z"},
                {"title": "B"},
            ]
            state.wiki_tab.labels = ["Z", "B"]
            state.wiki_tab.cursor = 0

        monkeypatch.setattr(wiki_tab, "_load_wikis", fake_load)

        wiki_tab._on_reload(state)

        # B は新一覧の index=1 なので復元される
        assert state.wiki_tab.cursor == 1
        # texts キャッシュはクリアされる (再読込後の本文は最新を取り直す)
        assert state.wiki_tab.texts == {}

    def test_falls_back_to_top_when_title_missing(self, monkeypatch):
        """前回のタイトルが新一覧に無ければ cursor=0 のまま"""
        state = TuiState()
        state.wiki_tab.loaded = True
        state.wiki_tab.pages = [{"title": "deleted"}]
        state.wiki_tab.cursor = 0

        def fake_load(state):
            state.wiki_tab.loaded = True
            state.wiki_tab.pages = [{"title": "new1"}, {"title": "new2"}]
            state.wiki_tab.cursor = 0

        monkeypatch.setattr(wiki_tab, "_load_wikis", fake_load)

        wiki_tab._on_reload(state)

        assert state.wiki_tab.cursor == 0


class TestTimeEntryReload:
    """time_entry タブの _on_reload() は loaded を倒して取り直す"""

    def test_restores_cursor_by_id(self, monkeypatch):
        """同じ id の entry が残っていれば cursor をその位置に復元する"""
        state = TuiState()
        state.time_entry_tab.loaded = True
        state.time_entry_tab.entries = [
            {"id": 100},
            {"id": 200},
            {"id": 300},
        ]
        state.time_entry_tab.cursor = 1  # id=200 にいる

        def fake_load(state):
            assert state.time_entry_tab.loaded is False
            state.time_entry_tab.loaded = True
            # 200 は残っているが順序が変わる
            state.time_entry_tab.entries = [
                {"id": 400},
                {"id": 200},
            ]
            state.time_entry_tab.cursor = 0

        monkeypatch.setattr(time_entry_tab, "_load_time_entries", fake_load)

        time_entry_tab._on_reload(state)

        assert state.time_entry_tab.cursor == 1

    def test_falls_back_to_top_when_id_missing(self, monkeypatch):
        """前回の id が新一覧に無ければ cursor=0 のまま"""
        state = TuiState()
        state.time_entry_tab.loaded = True
        state.time_entry_tab.entries = [{"id": 999}]
        state.time_entry_tab.cursor = 0

        def fake_load(state):
            state.time_entry_tab.loaded = True
            state.time_entry_tab.entries = [{"id": 111}, {"id": 222}]
            state.time_entry_tab.cursor = 0

        monkeypatch.setattr(time_entry_tab, "_load_time_entries", fake_load)

        time_entry_tab._on_reload(state)

        assert state.time_entry_tab.cursor == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
