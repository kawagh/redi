import argparse
from typing import cast

import pytest

from redi import config, config_schema
from redi.api.me import MyAccount
from redi.cli import config_command
from redi.cli.connection import ConnectionResult


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    """環境変数の有無で検証結果が変わるため、既定では未設定にしておく"""
    for name in config_schema.ENV_FALLBACK.values():
        monkeypatch.delenv(name, raising=False)


def _profile(**overrides) -> dict:
    return {
        "redmine_url": "https://redmine.example.com",
        "redmine_api_key": "secret",
    } | overrides


def _args(profile_name=None, all=False, no_connection=True) -> argparse.Namespace:
    return argparse.Namespace(
        profile_name=profile_name, all=all, no_connection=no_connection
    )


@pytest.fixture
def doc(monkeypatch) -> dict:
    """config_command が読む config.toml を差し替える"""
    document = {
        "default_profile": "main",
        "main": _profile(),
        "sub": _profile(),
    }
    monkeypatch.setattr(config_command, "load_toml", lambda: document)
    monkeypatch.setattr(config_command.config, "current_profile", "main")
    return document


@pytest.fixture
def connection_ok(monkeypatch) -> list[tuple[str, str]]:
    """疎通確認を成功させ、渡された接続先を捕捉する"""
    calls: list[tuple[str, str]] = []

    def fake_verify(api_client, messages) -> ConnectionResult:
        calls.append(
            (api_client.base_url, api_client.session.headers["X-Redmine-API-Key"])
        )
        user = cast("MyAccount", {"login": "kawagh"})
        return ConnectionResult(ok=True, user=user, error=None)

    monkeypatch.setattr(config_command, "verify_connection", fake_verify)
    return calls


class TestTargetSelection:
    """検証対象のプロファイルを決める"""

    def test_defaults_to_current_profile(self, doc, capsys):
        """プロファイル名を省略すると使用中のプロファイルを検証する"""
        config_command._handle_config_check(_args())

        out = capsys.readouterr().out
        assert "main:" in out
        assert "sub:" not in out

    def test_uses_given_profile(self, doc, capsys):
        """プロファイル名を指定するとそれだけを検証する"""
        config_command._handle_config_check(_args(profile_name="sub"))

        out = capsys.readouterr().out
        assert "sub:" in out
        assert "main:" not in out

    def test_all_checks_every_profile(self, doc, capsys):
        """--all は全プロファイルを検証する"""
        config_command._handle_config_check(_args(all=True))

        out = capsys.readouterr().out
        assert "main:" in out
        assert "sub:" in out

    def test_unknown_profile_exits(self, doc, capsys):
        """存在しないプロファイル名を指定したら exit 1"""
        with pytest.raises(SystemExit) as e:
            config_command._handle_config_check(_args(profile_name="missing"))

        assert e.value.code == 1
        assert "missing" in capsys.readouterr().err

    def test_no_profiles_exits(self, monkeypatch, capsys):
        """プロファイルが1つも無ければ exit 1"""
        monkeypatch.setattr(config_command, "load_toml", dict)

        with pytest.raises(SystemExit) as e:
            config_command._handle_config_check(_args())

        assert e.value.code == 1

    def test_no_target_profile_exits(self, doc, monkeypatch, capsys):
        """使用中のプロファイルが特定できなければ exit 1"""
        monkeypatch.setattr(config_command.config, "current_profile", None)

        with pytest.raises(SystemExit) as e:
            config_command._handle_config_check(_args())

        assert e.value.code == 1


class TestExitCode:
    """ERROR があるときだけ exit 1 する"""

    def test_valid_profile_does_not_exit(self, doc):
        """妥当なプロファイルなら例外を投げずに終わる"""
        config_command._handle_config_check(_args())

    def test_error_exits(self, doc, capsys):
        """ERROR があれば exit 1"""
        del doc["main"]["redmine_api_key"]

        with pytest.raises(SystemExit) as e:
            config_command._handle_config_check(_args())

        assert e.value.code == 1
        assert "ERROR" in capsys.readouterr().out

    def test_warning_does_not_exit(self, doc, capsys):
        """WARNING だけなら exit しない"""
        doc["main"]["language"] = "jp"

        config_command._handle_config_check(_args())

        assert "WARNING" in capsys.readouterr().out

    def test_reports_every_profile_before_exiting(self, doc, capsys):
        """先に壊れたプロファイルがあっても残りの検証結果を出してから exit する"""
        del doc["main"]["redmine_url"]

        with pytest.raises(SystemExit):
            config_command._handle_config_check(_args(all=True))

        out = capsys.readouterr().out
        assert "main:" in out
        assert "sub:" in out


class TestTopLevel:
    """プロファイルに属さない記述も報告する"""

    def test_reports_broken_default_profile(self, doc, capsys):
        """default_profile が実在しないプロファイルを指していれば ERROR"""
        doc["default_profile"] = "missing"

        with pytest.raises(SystemExit) as e:
            config_command._handle_config_check(_args(profile_name="main"))

        assert e.value.code == 1
        assert "default_profile" in capsys.readouterr().out


class TestConnection:
    """疎通確認はデフォルトで実行する"""

    def test_checks_connection_by_default(self, doc, connection_ok, capsys):
        """--no-connection なしなら疎通確認まで行う"""
        config_command._handle_config_check(_args(no_connection=False))

        assert connection_ok == [("https://redmine.example.com", "secret")]
        assert "kawagh" in capsys.readouterr().out

    def test_no_connection_skips(self, doc, connection_ok, capsys):
        """--no-connection ならスキーマ検証だけで終える"""
        config_command._handle_config_check(_args(no_connection=True))

        assert connection_ok == []

    def test_uses_profile_credentials(self, doc, connection_ok, monkeypatch):
        """環境変数ではなくプロファイル自身の接続先を叩く"""
        monkeypatch.setenv("REDMINE_URL", "https://other.example.com")

        config_command._handle_config_check(
            _args(profile_name="main", no_connection=False)
        )

        assert connection_ok == [("https://redmine.example.com", "secret")]

    def test_falls_back_to_env_credentials(self, doc, connection_ok, monkeypatch):
        """プロファイルに無い必須キーは実行時と同じく環境変数で補って確認する"""
        monkeypatch.setenv("REDMINE_API_KEY", "from-env")
        del doc["main"]["redmine_api_key"]

        config_command._handle_config_check(
            _args(profile_name="main", no_connection=False)
        )

        assert connection_ok == [("https://redmine.example.com", "from-env")]

    def test_skips_connection_when_schema_has_error(self, doc, connection_ok, capsys):
        """接続先が確定しないので疎通確認まで進めない"""
        del doc["main"]["redmine_url"]

        with pytest.raises(SystemExit):
            config_command._handle_config_check(_args(no_connection=False))

        assert connection_ok == []

    def test_connection_failure_exits(self, doc, monkeypatch, capsys):
        """疎通できなければ exit 1"""
        monkeypatch.setattr(
            config_command,
            "verify_connection",
            lambda *_: ConnectionResult(ok=False, user=None, error="401 Unauthorized"),
        )

        with pytest.raises(SystemExit) as e:
            config_command._handle_config_check(_args(no_connection=False))

        assert e.value.code == 1
        assert "401 Unauthorized" in capsys.readouterr().out


class TestEnvOverrideNote:
    """環境変数が設定されているときだけ注記を出す"""

    def test_prints_note_when_env_is_set(self, doc, monkeypatch, capsys):
        """実行時と結果がずれる唯一の要因なので注記する"""
        monkeypatch.setenv("REDMINE_URL", "https://other.example.com")

        config_command._handle_config_check(_args())

        assert "REDMINE_URL" in capsys.readouterr().out

    def test_no_note_without_env(self, doc, capsys):
        """環境変数が無ければ注記は出さない"""
        config_command._handle_config_check(_args())

        assert "REDMINE_URL" not in capsys.readouterr().out


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
