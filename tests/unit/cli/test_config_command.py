import argparse

import pytest

from redi import config
from redi.cli import config_command


def _create_args(**overrides) -> argparse.Namespace:
    values = {
        "config_command": "create",
        "profile_name": None,
        "url": None,
        "api_key": None,
        "project_id": None,
        "wiki_project_id": None,
        "editor": None,
        "language": None,
        "text_formatting": None,
        "set_default": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class TestConfigCreate:
    """`config create` は引数が足りなければ対話で補う"""

    @pytest.fixture
    def created(self, monkeypatch):
        """create_profile に渡された引数を記録する。デフォルトは追加プロファイル扱い"""
        calls: dict = {}

        def fake_create_profile(profile_name, profile):
            calls["profile_name"] = profile_name
            calls["profile"] = profile
            return config.CreateProfileResult(created=True, set_as_default=False)

        monkeypatch.setattr(config_command, "create_profile", fake_create_profile)
        monkeypatch.setattr(config_command, "list_profile_names", lambda: ["main"])
        monkeypatch.setattr(config_command, "inline_choice", lambda *_, **__: "no")
        return calls

    @pytest.fixture(autouse=True)
    def _prompted(self, monkeypatch):
        """対話に入った場合は URL と APIキーが埋まって返る"""
        monkeypatch.setattr(
            config_command,
            "prompt_connection_profile",
            lambda *_: config.Profile(
                redmine_url="http://example.com", redmine_api_key="k"
            ),
        )

    def test_args_only(self, created, monkeypatch):
        """プロファイル名/URL/APIキーが揃っていれば対話に入らない"""
        monkeypatch.setattr(
            config_command,
            "prompt_connection_profile",
            lambda *_: pytest.fail("対話に入らない想定"),
        )
        args = _create_args(profile_name="sub", url="http://example.com", api_key="k")

        config_command.handle_config(args)

        assert created["profile_name"] == "sub"
        assert created["profile"].redmine_url == "http://example.com"
        assert created["profile"].redmine_api_key == "k"

    def test_prompts_missing_values(self, created, monkeypatch):
        """APIキーが無ければ対話で接続情報を補い、引数の値は保つ"""
        monkeypatch.setattr(
            config_command,
            "prompt_connection_profile",
            lambda current, _: config.Profile(
                redmine_url=current.redmine_url,
                redmine_api_key="prompted_key",
                default_project_id="1",
            ),
        )
        args = _create_args(profile_name="sub", url="http://example.com", editor="vim")

        config_command.handle_config(args)

        assert created["profile"] == config.Profile(
            redmine_url="http://example.com",
            redmine_api_key="prompted_key",
            default_project_id="1",
            editor="vim",
        )

    def test_prompts_profile_name(self, created, monkeypatch):
        """プロファイル名が無ければ対話で入力させる"""
        monkeypatch.setattr(config_command, "prompt", lambda *_, **__: " sub ")

        config_command.handle_config(_create_args())

        assert created["profile_name"] == "sub"

    def test_confirm_set_default(self, created, monkeypatch):
        """他のプロファイルがある場合はデフォルトにするか確認する"""
        monkeypatch.setattr(config_command, "inline_choice", lambda *_, **__: "yes")
        set_default_calls: list[str] = []

        def fake_set_default_profile(name: str) -> bool:
            set_default_calls.append(name)
            return True

        monkeypatch.setattr(
            config_command, "set_default_profile", fake_set_default_profile
        )
        args = _create_args(profile_name="sub", url="http://example.com")

        config_command.handle_config(args)

        assert set_default_calls == ["sub"]

    def test_no_confirm_for_first_profile(self, created, monkeypatch):
        """最初のプロファイルは create_profile が自動でデフォルトにするため確認しない"""
        monkeypatch.setattr(config_command, "list_profile_names", list)
        monkeypatch.setattr(
            config_command,
            "inline_choice",
            lambda *_, **__: pytest.fail("確認しない想定"),
        )
        args = _create_args(profile_name="sub", url="http://example.com")

        config_command.handle_config(args)

        assert created["profile_name"] == "sub"

    def test_exits_when_not_created(self, monkeypatch):
        """作成に失敗したら exit 1 する"""
        monkeypatch.setattr(
            config_command,
            "create_profile",
            lambda **_: config.CreateProfileResult(created=False, set_as_default=False),
        )
        args = _create_args(profile_name="sub", url="http://example.com", api_key="k")

        with pytest.raises(SystemExit) as e:
            config_command.handle_config(args)

        assert e.value.code == 1


class TestUpdateFieldValues:
    """`config update` の更新項目の選択肢"""

    def test_offered_for_non_default_profile(self, monkeypatch):
        """デフォルト以外のプロファイルには set_default を出す"""
        monkeypatch.setattr(config_command, "get_default_profile", lambda: "main")

        keys = [k for k, _ in config_command._update_field_values("sub")]

        assert "set_default" in keys

    def test_hidden_for_default_profile(self, monkeypatch):
        """既にデフォルトのプロファイルには set_default を出さない"""
        monkeypatch.setattr(config_command, "get_default_profile", lambda: "main")

        keys = [k for k, _ in config_command._update_field_values("main")]

        assert "set_default" not in keys


class TestInteractiveFillConfigUpdateArgs:
    """`config update` の対話フローで更新項目を選ぶ"""

    def test_set_default_selected(self, monkeypatch):
        """set_default を選ぶと default_profile に対象プロファイルが入る"""
        monkeypatch.setattr(config_command, "read_profile", lambda _: config.Profile())
        monkeypatch.setattr(config_command, "get_default_profile", lambda: "main")
        monkeypatch.setattr(
            config_command, "inline_checkbox", lambda *_: ["set_default"]
        )
        args = argparse.Namespace(default_profile=None, profile_name=None)

        assert config_command._interactive_fill_config_update_args(args, "sub")

        assert args.default_profile == "sub"
        assert args.profile_name == "sub"

    def test_set_default_not_selected(self, monkeypatch):
        """set_default を選ばなければ default_profile は変わらない"""
        monkeypatch.setattr(config_command, "read_profile", lambda _: config.Profile())
        monkeypatch.setattr(config_command, "get_default_profile", lambda: "main")
        monkeypatch.setattr(config_command, "inline_checkbox", lambda *_: ["editor"])
        monkeypatch.setattr(config_command, "prompt", lambda *_, **__: "vim")
        args = argparse.Namespace(default_profile=None, profile_name=None, editor=None)

        assert config_command._interactive_fill_config_update_args(args, "sub")

        assert args.default_profile is None
        assert args.editor == "vim"
