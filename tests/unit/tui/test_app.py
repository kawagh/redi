from prompt_toolkit.utils import get_cwidth

from redi.tui import app
from redi.tui.state import TuiState


class TestBuildUserChoices:
    """_build_user_choices() は time_entry フィルタモーダルのユーザー選択肢を組み立てる"""

    def test_returns_specials_only_when_project_id_is_none(self):
        """project_id が None のとき (指定なし) + (自分) のみ返す"""
        choices = app._build_user_choices(None)
        assert [v for v, _ in choices] == [None, "me"]

    def test_includes_project_users_when_me_id_is_none(self, monkeypatch):
        """me_id 未指定なら project users はそのまま全件並ぶ"""
        monkeypatch.setattr(
            app,
            "fetch_project_users",
            lambda _project_id: [
                {"id": 5, "name": "Sandbox Developer"},
                {"id": 9, "name": "Other"},
            ],
        )
        choices = app._build_user_choices("1")
        assert [v for v, _ in choices] == [None, "me", "5", "9"]

    def test_excludes_self_when_me_id_matches_project_user(self, monkeypatch):
        """me_id と一致する project user は除外して『自分』との重複を防ぐ"""
        monkeypatch.setattr(
            app,
            "fetch_project_users",
            lambda _project_id: [
                {"id": 5, "name": "Sandbox Developer"},
                {"id": 9, "name": "Other"},
            ],
        )
        choices = app._build_user_choices("1", me_id="5")
        assert [v for v, _ in choices] == [None, "me", "9"]

    def test_keeps_all_users_when_me_id_not_in_project_users(self, monkeypatch):
        """me_id が project users に居なければ何も除外しない"""
        monkeypatch.setattr(
            app,
            "fetch_project_users",
            lambda _project_id: [{"id": 5, "name": "Sandbox Developer"}],
        )
        choices = app._build_user_choices("1", me_id="999")
        assert [v for v, _ in choices] == [None, "me", "5"]


class TestBuildAssigneeChoices:
    """_build_assignee_choices() は issue フィルタモーダルの担当者選択肢を組み立てる"""

    def test_returns_specials_only_when_project_id_is_none(self):
        """project_id が None のとき (指定なし) + (自分) + (未割当) のみ返す"""
        choices = app._build_assignee_choices(None)
        assert [v for v, _ in choices] == [None, "me", "!*"]

    def test_includes_project_users_when_me_id_is_none(self, monkeypatch):
        """me_id 未指定なら project users はそのまま全件並ぶ"""
        monkeypatch.setattr(
            app,
            "fetch_project_users",
            lambda _project_id: [
                {"id": 5, "name": "Sandbox Developer"},
                {"id": 9, "name": "Other"},
            ],
        )
        choices = app._build_assignee_choices("1")
        assert [v for v, _ in choices] == [None, "me", "!*", "5", "9"]

    def test_excludes_self_when_me_id_matches_project_user(self, monkeypatch):
        """me_id と一致する project user は除外して『自分』との重複を防ぐ"""
        monkeypatch.setattr(
            app,
            "fetch_project_users",
            lambda _project_id: [
                {"id": 5, "name": "Sandbox Developer"},
                {"id": 9, "name": "Other"},
            ],
        )
        choices = app._build_assignee_choices("1", me_id="5")
        assert [v for v, _ in choices] == [None, "me", "!*", "9"]

    def test_keeps_all_users_when_me_id_not_in_project_users(self, monkeypatch):
        """me_id が project users に居なければ何も除外しない"""
        monkeypatch.setattr(
            app,
            "fetch_project_users",
            lambda _project_id: [{"id": 5, "name": "Sandbox Developer"}],
        )
        choices = app._build_assignee_choices("1", me_id="999")
        assert [v for v, _ in choices] == [None, "me", "!*", "5"]


def _rendered_lines(parts) -> list[str]:
    return "".join(text for _style, text in parts).split("\n")


class TestRenderHelp:
    """_render_help() は各タブのヘルプ本文と末尾のバージョンを組み立てる"""

    def test_shows_version_at_last_line(self):
        """最終行に redi のバージョンを表示する"""
        lines = _rendered_lines(app._render_help(TuiState()))
        assert lines[-1].strip() == app._help_version_label()

    def test_version_line_is_right_aligned(self):
        """バージョン行は本文の最大幅に右寄せする (右下に表示)"""
        for tab in app.TABS:
            state = TuiState()
            state.tab = tab
            lines = _rendered_lines(app._render_help(state))
            body_width = max(get_cwidth(line) for line in lines[:-1])
            assert get_cwidth(lines[-1]) == body_width
            assert lines[-1].endswith(app._help_version_label())

    def test_blank_line_before_version(self):
        """バージョン行の直前は空行にして本文と分ける"""
        lines = _rendered_lines(app._render_help(TuiState()))
        assert lines[-2] == ""
