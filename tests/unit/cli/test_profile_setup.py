from typing import cast

import pytest

from redi.api.project import Project
from redi.cli import profile_setup
from redi.config import Profile
from redi.i18n.en import En


class TestPromptConnectionProfile:
    """設定済みの項目は聞き直さず、接続確認だけ行う"""

    @pytest.fixture(autouse=True)
    def _connection_ok(self, monkeypatch):
        monkeypatch.setattr(
            profile_setup,
            "_verify_connection",
            lambda *_: {"login": "alice", "firstname": "Alice", "lastname": "A"},
        )

    def test_keeps_given_values(self, monkeypatch):
        """全項目が揃っていれば入力もプロジェクト取得も行わない"""
        monkeypatch.setattr(
            profile_setup, "prompt", lambda *_, **__: pytest.fail("入力しない想定")
        )
        monkeypatch.setattr(
            profile_setup,
            "_fetch_projects",
            lambda *_: pytest.fail("プロジェクトを取得しない想定"),
        )
        current = Profile(
            redmine_url="http://example.com",
            redmine_api_key="k",
            default_project_id="1",
            wiki_project_id="2",
        )

        assert profile_setup.prompt_connection_profile(current, En()) == current

    def test_prompts_missing_project(self, monkeypatch):
        """未設定のプロジェクトだけ選ばせる"""
        monkeypatch.setattr(
            profile_setup,
            "_fetch_projects",
            lambda *_: [{"id": 2, "name": "wiki"}],
        )
        monkeypatch.setattr(profile_setup, "_select_project_id", lambda *_: "2")
        current = Profile(
            redmine_url="http://example.com",
            redmine_api_key="k",
            default_project_id="1",
        )

        profile = profile_setup.prompt_connection_profile(current, En())

        assert profile.default_project_id == "1"
        assert profile.wiki_project_id == "2"

    def test_no_projects(self, monkeypatch):
        """プロジェクトが取得できなければ project_id は未設定のままにする"""
        monkeypatch.setattr(profile_setup, "_fetch_projects", lambda *_: [])
        current = Profile(redmine_url="http://example.com", redmine_api_key="k")

        profile = profile_setup.prompt_connection_profile(current, En())

        assert profile.default_project_id is None
        assert profile.wiki_project_id is None


class TestFetchProjectChoices:
    """渡された接続情報でプロジェクト一覧を取る"""

    def test_uses_given_credentials(self, monkeypatch):
        """default_profile ではなく、渡された URL と API キーの接続先から取る"""
        used: list[tuple[str, str]] = []

        def fake_fetch(api_client, _messages):
            used.append(
                (api_client.base_url, api_client.session.headers["X-Redmine-API-Key"])
            )
            return [{"id": 1, "name": "p"}]

        monkeypatch.setattr(profile_setup, "_fetch_projects", fake_fetch)

        projects = profile_setup.fetch_project_choices(
            "http://sub.example.com", "sub-key", En()
        )

        assert projects == [{"id": 1, "name": "p"}]
        assert used == [("http://sub.example.com", "sub-key")]

    @pytest.mark.parametrize(
        ("url", "api_key"), [(None, "k"), ("http://example.com", None)]
    )
    def test_empty_without_credentials(self, monkeypatch, url, api_key):
        """接続情報が揃わなければ取得せず空を返す"""
        monkeypatch.setattr(
            profile_setup,
            "_fetch_projects",
            lambda *_: pytest.fail("プロジェクトを取得しない想定"),
        )

        assert profile_setup.fetch_project_choices(url, api_key, En()) == []


class TestSelectOrPromptProjectId:
    """プロジェクト一覧から選ばせ、一覧が無ければ自由入力させる"""

    def test_selects_from_projects(self, monkeypatch):
        """一覧があれば現在値にカーソルを合わせて選ばせる"""
        calls: list[str | None] = []

        def fake_inline_choice(_message, _options, default=None):
            calls.append(default)
            return "2"

        monkeypatch.setattr(profile_setup, "inline_choice", fake_inline_choice)
        monkeypatch.setattr(
            profile_setup, "prompt", lambda *_, **__: pytest.fail("入力しない想定")
        )

        project_id = profile_setup.select_or_prompt_project_id(
            "select",
            "input",
            cast("list[Project]", [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]),
            "1",
            En(),
        )

        assert project_id == "2"
        assert calls == ["1"]

    def test_prompts_without_projects(self, monkeypatch):
        """一覧が取れなかった場合は ID を自由入力させる"""
        monkeypatch.setattr(
            profile_setup,
            "inline_choice",
            lambda *_, **__: pytest.fail("選択させない想定"),
        )
        monkeypatch.setattr(profile_setup, "prompt", lambda *_, **__: " 3 ")

        project_id = profile_setup.select_or_prompt_project_id(
            "select", "input", [], "1", En()
        )

        assert project_id == "3"
