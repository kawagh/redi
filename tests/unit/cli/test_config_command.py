import argparse

import pytest

from redi import config, config_schema
from redi.api.account import ConnectionResult
from redi.cli import config_command


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

    def fake_verify(url: str, api_key: str, messages) -> ConnectionResult:
        calls.append((url, api_key))
        return ConnectionResult(ok=True, user={"login": "kawagh"}, error=None)

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
        assert "missing" in capsys.readouterr().out

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
            lambda url, key, messages: ConnectionResult(
                ok=False, user=None, error="401 Unauthorized"
            ),
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
