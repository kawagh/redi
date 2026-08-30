"""TUI のプロジェクト切替 (p キー) の単体テスト。"""

from collections.abc import Callable
from typing import cast

import pytest
import requests

from redi import config
from redi.api.project import Project
from redi.api.time_entry import TimeEntry
from redi.i18n import messages
from redi.tui import app_render, project_modal
from redi.tui.issue import issue_tab
from redi.tui.state import IssueFilter, TimeEntryFilter, TuiState
from redi.tui.tab import TabView, noop, noop_jump
from redi.tui.tabs import TABS
from redi.tui.time_entry import time_entry_tab

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


class TestOpenProjectModal:
    """open_project_modal() は選択肢を構築し現在プロジェクトへカーソルを合わせる"""

    def test_cursor_on_switched_project(self, monkeypatch):
        """切替済みならそのプロジェクトの位置にカーソルが乗り active_value が入る"""
        monkeypatch.setattr(project_modal, "list_projects", lambda **kwargs: PROJECTS)
        state = TuiState(project_id="2")

        project_modal.open_project_modal(state)

        assert state.project_modal.show is True
        assert state.project_modal.choices == [("2", "Beta"), ("1", "Alpha")]
        assert state.project_modal.cursor == 0
        assert state.project_modal.active_value == "2"

    def test_unswitched_marks_config_default_project(self, monkeypatch):
        """未切替でも toml の default_project_id のプロジェクトが active になる"""
        monkeypatch.setattr(project_modal, "list_projects", lambda **kwargs: PROJECTS)
        monkeypatch.setattr(config, "default_project_id", "1")
        state = TuiState()

        project_modal.open_project_modal(state)

        assert state.project_modal.active_value == "1"
        assert state.project_modal.cursor == 1

    def test_config_identifier_is_resolved_to_id(self, monkeypatch):
        """config には identifier も設定できるので id に解決して保持する"""
        monkeypatch.setattr(project_modal, "list_projects", lambda **kwargs: PROJECTS)
        monkeypatch.setattr(config, "default_project_id", "beta")
        state = TuiState()

        project_modal.open_project_modal(state)

        assert state.project_modal.active_value == "2"
        assert state.project_modal.cursor == 0

    def test_cursor_top_when_no_current_project(self, monkeypatch):
        """未切替かつ config 未設定ならカーソルは先頭で active 無し"""
        monkeypatch.setattr(project_modal, "list_projects", lambda **kwargs: PROJECTS)
        monkeypatch.setattr(config, "default_project_id", None)
        state = TuiState()

        project_modal.open_project_modal(state)

        assert state.project_modal.cursor == 0
        assert state.project_modal.active_value is None

    def test_request_error_goes_to_error_modal(self, monkeypatch):
        """取得失敗時は error modal に流し、モーダルは開かない"""

        def boom(**kwargs) -> list[Project]:
            raise requests.exceptions.RequestException("down")

        monkeypatch.setattr(project_modal, "list_projects", boom)
        state = TuiState()

        project_modal.open_project_modal(state)

        assert state.project_modal.show is False
        assert state.error_modal is not None
        assert "down" in state.error_modal


class TestApplyProjectSwitch:
    """apply_project_switch() は全タブを新プロジェクトで取り直す"""

    def test_switch_resets_tabs_and_reloads_issues(self, monkeypatch):
        reloaded: list[str | None] = []
        monkeypatch.setattr(
            project_modal,
            "reload_with_filter",
            lambda state: reloaded.append(state.project_id),
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

        project_modal.apply_project_switch(state, "2", "Beta")

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

    def test_numeric_user_filters_are_cleared(self, monkeypatch):
        """数値 ID のフィルタは旧プロジェクトのユーザーを指すのでクリアされる"""
        monkeypatch.setattr(project_modal, "reload_with_filter", lambda state: None)
        state = TuiState()
        state.issue_tab.filter = IssueFilter(
            status_id="*",
            status_label="all",
            assigned_to_id="123",
            assigned_to_label="Alice",
        )
        state.time_entry_tab.filter = TimeEntryFilter(user_id="123", user_label="Alice")

        project_modal.apply_project_switch(state, "2", "Beta")

        # status はプロジェクト非依存なので保持される
        assert state.issue_tab.filter.status_id == "*"
        assert state.issue_tab.filter.assigned_to_id is None
        assert state.time_entry_tab.filter.user_id == TimeEntryFilter().user_id

    def test_query_filter_is_cleared(self, monkeypatch):
        """クエリはプロジェクト固有のものが混ざるので切替時にクリアされる"""
        monkeypatch.setattr(project_modal, "reload_with_filter", lambda state: None)
        state = TuiState()
        state.issue_tab.filter = IssueFilter(query_id="7", query_label="My open issues")

        project_modal.apply_project_switch(state, "2", "Beta")

        assert state.issue_tab.filter.query_id is None
        assert state.issue_tab.filter.is_active() is False

    def test_special_filters_are_preserved(self, monkeypatch):
        """me / 未割当などの特殊値はプロジェクト非依存なので保持される"""
        monkeypatch.setattr(project_modal, "reload_with_filter", lambda state: None)
        state = TuiState()
        state.issue_tab.filter = IssueFilter(
            assigned_to_id="me", assigned_to_label="自分"
        )
        state.time_entry_tab.filter = TimeEntryFilter(user_id="me", user_label="自分")

        project_modal.apply_project_switch(state, "2", "Beta")

        assert state.issue_tab.filter.assigned_to_id == "me"
        assert state.time_entry_tab.filter.user_id == "me"

    def test_current_tab_time_entries_reloads_immediately(self, monkeypatch):
        monkeypatch.setattr(project_modal, "reload_with_filter", lambda state: None)
        activated: list[str] = []
        monkeypatch.setitem(
            TABS,
            "time_entries",
            _fake_tab(lambda s: activated.append("time_entries")),
        )
        state = TuiState()
        state.tab = "time_entries"

        project_modal.apply_project_switch(state, "2", "Beta")

        assert activated == ["time_entries"]

    def test_issues_tab_does_not_activate_others(self, monkeypatch):
        monkeypatch.setattr(project_modal, "reload_with_filter", lambda state: None)
        activated: list[str] = []
        monkeypatch.setitem(
            TABS,
            "time_entries",
            _fake_tab(lambda s: activated.append("time_entries")),
        )
        monkeypatch.setitem(TABS, "wiki", _fake_tab(lambda s: activated.append("wiki")))
        state = TuiState()
        state.tab = "issues"

        project_modal.apply_project_switch(state, "2", "Beta")

        assert activated == []


class TestRenderTabs:
    """render_tabs() は現在のプロジェクトを常に表示する"""

    @pytest.fixture(autouse=True)
    def hide_profile_label(self, monkeypatch):
        """プロファイル名も同じ行に出るので、実行環境の config に左右されないようにする"""
        monkeypatch.setattr(config, "current_profile", None)

    def test_shows_config_project_when_unswitched(self, monkeypatch):
        monkeypatch.setattr(config, "default_project_id", "redidemo")
        state = TuiState()

        rendered = "".join(text for _style, text in app_render.render_tabs(state))

        assert "[project: redidemo]" in rendered

    def test_switched_label_takes_precedence(self, monkeypatch):
        monkeypatch.setattr(config, "default_project_id", "redidemo")
        state = TuiState(project_id="2", project_label="Beta")

        rendered = "".join(text for _style, text in app_render.render_tabs(state))

        assert "[project: Beta]" in rendered
        assert "redidemo" not in rendered

    def test_no_label_when_nothing_is_set(self, monkeypatch):
        monkeypatch.setattr(config, "default_project_id", None)
        state = TuiState()

        rendered = "".join(text for _style, text in app_render.render_tabs(state))

        assert "[project:" not in rendered


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
            time_entry_tab.time_entry_service,
            "fetch_page",
            fake_fetch_time_entries_page,
        )
        monkeypatch.setattr(
            time_entry_tab.time_entry_service,
            "fetch_issue_subjects",
            lambda entries: {},
        )
        state = TuiState(project_id="2")
        state.page_size = 5

        time_entry_tab._fetch_page_with_subjects(state, 0)

        assert captured["project_id"] == "2"
