import argparse
from typing import ClassVar

import pytest

from redi import config
from redi.cli import config_command, confirm
from redi.cli.interactive import InputCanceledException
from redi.i18n import messages


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


def _delete_args(**overrides) -> argparse.Namespace:
    values = {"config_command": "delete", "profile_name": None, "yes": False}
    values.update(overrides)
    return argparse.Namespace(**values)


class TestConfigDelete:
    """`config delete` は確認を挟んでプロファイルを消す"""

    @pytest.fixture
    def deleted(self, monkeypatch):
        """delete_profile に渡されたプロファイル名を記録する"""
        calls: list[str] = []

        def fake_delete_profile(profile_name):
            calls.append(profile_name)
            return config.DeleteProfileResult(deleted=True, default_removed=False)

        monkeypatch.setattr(config_command, "delete_profile", fake_delete_profile)
        return calls

    def test_confirms_before_delete(self, deleted, monkeypatch, capsys):
        """引数のプロファイル名を示して yes/No で確認してから消す"""
        monkeypatch.setattr(confirm, "prompt", lambda *_, **__: "yes")
        monkeypatch.setattr(
            config_command,
            "inline_choice",
            lambda *_, **__: pytest.fail("対話選択に入らない想定"),
        )

        config_command.handle_config(_delete_args(profile_name="sub"))

        assert deleted == ["sub"]
        out = capsys.readouterr().out
        assert "sub" in out

    def test_cancel_keeps_profile(self, deleted, monkeypatch):
        """確認で No ならキャンセルとして通知し、消さない"""
        monkeypatch.setattr(confirm, "prompt", lambda *_, **__: "")

        with pytest.raises(InputCanceledException):
            config_command.handle_config(_delete_args(profile_name="sub"))

        assert deleted == []

    def test_yes_skips_confirm(self, deleted, monkeypatch):
        """--yes なら確認を挟まずに消す (非 TTY 向け)"""
        monkeypatch.setattr(
            confirm, "prompt", lambda *_, **__: pytest.fail("確認しない想定")
        )

        config_command.handle_config(_delete_args(profile_name="sub", yes=True))

        assert deleted == ["sub"]

    def test_prompts_profile_when_omitted(self, deleted, monkeypatch):
        """プロファイル名を省略したら一覧から選ばせ、default_profile には印を付ける"""
        monkeypatch.setattr(
            config_command, "list_profile_names", lambda: ["main", "sub"]
        )
        monkeypatch.setattr(config_command, "get_default_profile", lambda: "main")
        shown: dict = {}

        def fake_inline_choice(message, options, **_):
            shown["options"] = options
            return "sub"

        monkeypatch.setattr(config_command, "inline_choice", fake_inline_choice)

        config_command.handle_config(_delete_args(yes=True))

        assert deleted == ["sub"]
        assert shown["options"] == [("main", "main (default)"), ("sub", "sub")]

    def test_exits_when_no_profiles(self, deleted, monkeypatch, capsys):
        """プロファイルが 1 つも無ければ選ばせずに exit 1 する"""
        monkeypatch.setattr(config_command, "list_profile_names", list)

        with pytest.raises(SystemExit) as e:
            config_command.handle_config(_delete_args(yes=True))

        assert e.value.code == 1
        assert deleted == []

    def test_exits_when_not_deleted(self, monkeypatch):
        """消せなかったら exit 1 する"""
        monkeypatch.setattr(
            config_command,
            "delete_profile",
            lambda _: config.DeleteProfileResult(deleted=False, default_removed=False),
        )

        with pytest.raises(SystemExit) as e:
            config_command.handle_config(_delete_args(profile_name="main", yes=True))

        assert e.value.code == 1

    def test_notifies_default_removed(self, monkeypatch, capsys):
        """最後のプロファイルと一緒に default_profile も消したことを知らせる"""
        monkeypatch.setattr(
            config_command,
            "delete_profile",
            lambda _: config.DeleteProfileResult(deleted=True, default_removed=True),
        )

        config_command.handle_config(_delete_args(profile_name="main", yes=True))

        out = capsys.readouterr().out
        assert messages.profile_deleted.format(name="main") in out
        assert messages.default_profile_removed in out


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


class TestUpdateFieldOptions:
    """`config update` の更新項目の選択肢に現在値を添える"""

    _field_values: ClassVar[list[tuple[str, str]]] = [
        ("url", "redmine_url"),
        ("api_key", "redmine_api_key"),
        ("editor", "editor"),
    ]

    def test_shows_current_value(self):
        """設定済みの項目には現在値を添える"""
        current = config.Profile(redmine_url="http://example.com", editor="vim")

        options = dict(
            config_command._update_field_options(self._field_values, current)
        )

        assert options["url"] == "redmine_url # http://example.com"
        assert options["editor"] == "editor # vim"

    def test_unset_value_not_shown(self):
        """未設定の項目はラベルだけにする"""
        options = dict(
            config_command._update_field_options(self._field_values, config.Profile())
        )

        assert options["editor"] == "editor"

    def test_api_key_not_shown(self):
        """API キーは設定済みでも値を出さない"""
        current = config.Profile(redmine_api_key="secret")

        options = dict(
            config_command._update_field_options(self._field_values, current)
        )

        assert options["api_key"] == "redmine_api_key"
        assert "secret" not in str(options)


class TestConfigShow:
    """`config` の表示は他リソースと同じく list (全プロファイル) / view (現在のプロファイル) で分ける"""

    @pytest.fixture
    def called(self, monkeypatch):
        """show_all_profiles / show_config のどちらが呼ばれたかを記録する"""
        calls: list[str] = []
        monkeypatch.setattr(
            config_command, "show_all_profiles", lambda: calls.append("list")
        )
        monkeypatch.setattr(config_command, "show_config", lambda: calls.append("view"))
        return calls

    @pytest.mark.parametrize("cmd", ["list", "l"])
    def test_list_shows_all_profiles(self, called, cmd):
        """`config list` は全プロファイルを表示する"""
        config_command.handle_config(argparse.Namespace(config_command=cmd))

        assert called == ["list"]

    @pytest.mark.parametrize("cmd", ["view", "v"])
    def test_view_shows_current_profile(self, called, cmd):
        """`config view` は現在のプロファイルを表示する"""
        config_command.handle_config(argparse.Namespace(config_command=cmd))

        assert called == ["view"]

    def test_no_subcommand_is_list(self, called):
        """サブコマンド未指定の `redi config` は list 相当にする"""
        config_command.handle_config(argparse.Namespace(config_command=None))

        assert called == ["list"]


class TestConfigParser:
    """`config` に `--full` は無く、表示はサブコマンドで分ける"""

    @pytest.fixture
    def parser(self):
        parser = argparse.ArgumentParser()
        config_command.add_config_parser(parser.add_subparsers(dest="command"), [])
        return parser

    def test_full_is_rejected(self, parser, capsys):
        """`--full` は他コマンドの `--format json` と意味が違うため受け付けない"""
        with pytest.raises(SystemExit):
            parser.parse_args(["config", "--full"])

    @pytest.mark.parametrize(
        "argv", [["config"], ["config", "list"], ["config", "view"]]
    )
    def test_show_subcommands_are_accepted(self, parser, argv):
        """`config` / `config list` / `config view` を引数無しで受け付ける"""
        parser.parse_args(argv)
