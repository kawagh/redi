import argparse

from redi.cli import config_command


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
        monkeypatch.setattr(config_command, "read_profile_values", lambda _: {})
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
        monkeypatch.setattr(config_command, "read_profile_values", lambda _: {})
        monkeypatch.setattr(config_command, "get_default_profile", lambda: "main")
        monkeypatch.setattr(config_command, "inline_checkbox", lambda *_: ["editor"])
        monkeypatch.setattr(config_command, "prompt", lambda *_, **__: "vim")
        args = argparse.Namespace(default_profile=None, profile_name=None, editor=None)

        assert config_command._interactive_fill_config_update_args(args, "sub")

        assert args.default_profile is None
        assert args.editor == "vim"
