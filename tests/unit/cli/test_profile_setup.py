import pytest

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
