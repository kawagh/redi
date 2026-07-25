"""TUI のプロジェクト切替 (p キー) の単体テスト。"""

from collections.abc import Callable
from typing import cast

import requests

from redi import config
from redi.api.project import Project
from redi.api.time_entry import TimeEntry
from redi.i18n import messages
from redi.tui import app, issue_tab, time_entry_tab
from redi.tui.state import IssueFilter, TimeEntryFilter, TuiState
from redi.tui.tab import TabView, noop, noop_jump

PROJECTS = cast(
    list[Project],
    [
        {"id": 1, "name": "Alpha", "identifier": "alpha"},
        {"id": 2, "name": "Beta", "identifier": "beta"},
    ],
)


def _fake_tab(on_activate: Callable[[TuiState], None]) -> TabView:
    return TabView(
        label="fake",
        render_list=lambda s: [],
        render_preview=lambda s: [],
        status_hint=lambda s: "",
        on_up=noop,
        on_down=noop,
        on_goto_top=noop,
        on_goto_bottom=noop,
        on_jump_to_id=noop_jump,
        on_enter=noop,
        on_page_forward=noop,
        on_page_backward=noop,
        on_open_web=noop,
        on_open_web_by_id=noop_jump,
        on_activate=on_activate,
        on_reload=noop,
        on_action_key=lambda s, k: None,
        on_search=lambda *args, **kwargs: None,
        get_cursor_y=lambda s: 0,
        help_lines=[],
    )


class TestBuildProjectChoices:
    """_build_project_choices() は fetch_projects() を (id, name) の組に変換する"""

    def test_converts_projects(self, monkeypatch):
        monkeypatch.setattr(app, "fetch_projects", lambda: PROJECTS)
        assert app._build_project_choices() == [("1", "Alpha"), ("2", "Beta")]


class TestOpenProjectModal:
    """open_project_modal() は選択肢を構築し現在プロジェクトへカーソルを合わせる"""

    def test_cursor_on_switched_project(self, monkeypatch):
        """切替済みならそのプロジェクトの位置にカーソルが乗る"""
        monkeypatch.setattr(app, "fetch_projects", lambda: PROJECTS)
        state = TuiState(project_id="2")

        app.open_project_modal(state)

        assert state.project_modal.show is True
        assert state.project_modal.choices == [("1", "Alpha"), ("2", "Beta")]
        assert state.project_modal.cursor == 1

    def test_cursor_matches_config_identifier(self, monkeypatch):
        """config には identifier も設定できるので identifier でも位置を探す"""
        monkeypatch.setattr(app, "fetch_projects", lambda: PROJECTS)
        monkeypatch.setattr(config, "default_project_id", "beta")
        state = TuiState()

        app.open_project_modal(state)

        assert state.project_modal.cursor == 1

    def test_cursor_top_when_no_current_project(self, monkeypatch):
        """未切替かつ config 未設定ならカーソルは先頭"""
        monkeypatch.setattr(app, "fetch_projects", lambda: PROJECTS)
        monkeypatch.setattr(config, "default_project_id", None)
        state = TuiState()

        app.open_project_modal(state)

        assert state.project_modal.cursor == 0

    def test_request_error_goes_to_error_modal(self, monkeypatch):
        """取得失敗時は error modal に流し、モーダルは開かない"""

        def boom() -> list[Project]:
            raise requests.exceptions.RequestException("down")

        monkeypatch.setattr(app, "fetch_projects", boom)
        state = TuiState()

        app.open_project_modal(state)

        assert state.project_modal.show is False
        assert state.error_modal is not None
        assert "down" in state.error_modal


class TestApplyProjectSwitch:
    """apply_project_switch() は全タブを新プロジェクトで取り直す"""

    def test_switch_resets_tabs_and_reloads_issues(self, monkeypatch):
        reloaded: list[str | None] = []
        monkeypatch.setattr(
            app, "reload_with_filter", lambda state: reloaded.append(state.project_id)
        )
        state = TuiState()
        state.page_size = 5
        state.project_modal.show = True
        state.preview_scroll = 3
        state.time_entry_tab.loaded = True
        state.time_entry_tab.entries = cast(list[TimeEntry], [{"id": 1}])
        state.wiki_tab.loaded = True
        # texts はタイトルのみがキーなので、残すと別プロジェクトの同名ページに
        # 旧本文が表示されてしまう。クリアされることを確認する。
        state.wiki_tab.texts = {"Home": "old body"}

        app.apply_project_switch(state, "2", "Beta")

        assert state.project_id == "2"
        assert state.project_label == "Beta"
        assert state.project_modal.show is False
        # issues は遅延再取得できないため切替時に即時取り直す
        assert reloaded == ["2"]
        assert state.time_entry_tab.loaded is False
        assert state.time_entry_tab.entries == []
        assert state.wiki_tab.loaded is False
        assert state.wiki_tab.texts == {}
        assert state.preview_scroll == 0
        assert state.flash_message == messages.tui_flash_project_switched.format(
            name="Beta"
        )

    def test_clear_resets_override(self, monkeypatch):
        monkeypatch.setattr(app, "reload_with_filter", lambda state: None)
        state = TuiState(project_id="2", project_label="Beta")

        app.apply_project_switch(state, None, "")

        assert state.project_id is None
        assert state.project_label == ""
        assert state.flash_message == messages.tui_flash_project_cleared

    def test_numeric_user_filters_are_cleared(self, monkeypatch):
        """数値 ID のフィルタは旧プロジェクトのユーザーを指すのでクリアされる"""
        monkeypatch.setattr(app, "reload_with_filter", lambda state: None)
        state = TuiState()
        state.issue_tab.filter = IssueFilter(
            status_id="*",
            status_label="all",
            assigned_to_id="123",
            assigned_to_label="Alice",
        )
        state.time_entry_tab.filter = TimeEntryFilter(user_id="123", user_label="Alice")

        app.apply_project_switch(state, "2", "Beta")

        # status はプロジェクト非依存なので保持される
        assert state.issue_tab.filter.status_id == "*"
        assert state.issue_tab.filter.assigned_to_id is None
        assert state.time_entry_tab.filter.user_id == TimeEntryFilter().user_id

    def test_special_filters_are_preserved(self, monkeypatch):
        """me / 未割当などの特殊値はプロジェクト非依存なので保持される"""
        monkeypatch.setattr(app, "reload_with_filter", lambda state: None)
        state = TuiState()
        state.issue_tab.filter = IssueFilter(
            assigned_to_id="me", assigned_to_label="自分"
        )
        state.time_entry_tab.filter = TimeEntryFilter(user_id="me", user_label="自分")

        app.apply_project_switch(state, "2", "Beta")

        assert state.issue_tab.filter.assigned_to_id == "me"
        assert state.time_entry_tab.filter.user_id == "me"

    def test_current_tab_time_entries_reloads_immediately(self, monkeypatch):
        monkeypatch.setattr(app, "reload_with_filter", lambda state: None)
        activated: list[str] = []
        monkeypatch.setitem(
            app.TABS,
            "time_entries",
            _fake_tab(lambda s: activated.append("time_entries")),
        )
        state = TuiState()
        state.tab = "time_entries"

        app.apply_project_switch(state, "2", "Beta")

        assert activated == ["time_entries"]

    def test_issues_tab_does_not_activate_others(self, monkeypatch):
        monkeypatch.setattr(app, "reload_with_filter", lambda state: None)
        activated: list[str] = []
        monkeypatch.setitem(
            app.TABS,
            "time_entries",
            _fake_tab(lambda s: activated.append("time_entries")),
        )
        monkeypatch.setitem(
            app.TABS, "wiki", _fake_tab(lambda s: activated.append("wiki"))
        )
        state = TuiState()
        state.tab = "issues"

        app.apply_project_switch(state, "2", "Beta")

        assert activated == []


class TestEffectiveProjectId:
    """effective_project_id() は override > config の優先順位で解決する"""

    def test_override_wins(self, monkeypatch):
        monkeypatch.setattr(config, "default_project_id", "5")
        monkeypatch.setattr(config, "wiki_project_id", "7")
        state = TuiState(project_id="2")

        assert state.effective_project_id() == "2"
        # 明示切替は wiki_project_id より優先する
        assert state.effective_wiki_project_id() == "2"

    def test_falls_back_to_config(self, monkeypatch):
        monkeypatch.setattr(config, "default_project_id", "5")
        monkeypatch.setattr(config, "wiki_project_id", "7")
        state = TuiState()

        assert state.effective_project_id() == "5"
        assert state.effective_wiki_project_id() == "7"

    def test_wiki_falls_back_to_default_project(self, monkeypatch):
        monkeypatch.setattr(config, "default_project_id", "5")
        monkeypatch.setattr(config, "wiki_project_id", None)
        state = TuiState()

        assert state.effective_wiki_project_id() == "5"

    def test_none_when_nothing_is_set(self, monkeypatch):
        monkeypatch.setattr(config, "default_project_id", None)
        monkeypatch.setattr(config, "wiki_project_id", None)
        state = TuiState()

        assert state.effective_project_id() is None
        assert state.effective_wiki_project_id() is None


class TestFetchUsesEffectiveProject:
    """各タブの fetch には切替後のプロジェクト id が渡る"""

    def test_issue_fetch_uses_switched_project(self, monkeypatch):
        captured: dict = {}

        def fake_fetch_issues_page(**kwargs):
            captured.update(kwargs)
            return {"issues": [], "total_count": 0}

        monkeypatch.setattr(issue_tab, "fetch_issues_page", fake_fetch_issues_page)
        state = TuiState(project_id="2")
        state.page_size = 5

        issue_tab.fetch_issues_with_filter(state, 0)

        assert captured["project_id"] == "2"

    def test_time_entry_fetch_uses_switched_project(self, monkeypatch):
        captured: dict = {}

        def fake_fetch_time_entries_page(**kwargs):
            captured.update(kwargs)
            return {"time_entries": [], "total_count": 0}

        monkeypatch.setattr(
            time_entry_tab, "fetch_time_entries_page", fake_fetch_time_entries_page
        )
        monkeypatch.setattr(
            time_entry_tab, "fetch_issue_subjects", lambda issue_ids: {}
        )
        state = TuiState(project_id="2")
        state.page_size = 5

        time_entry_tab._fetch_page_with_subjects(state, 0)

        assert captured["project_id"] == "2"
