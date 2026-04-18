import textwrap
import tomllib

import pytest

from redi import config


class TestCreateProfile:
    """create_profile()はconfig.tomlに新しいプロファイルセクションを追加する"""

    def test_creates_new_profile_section(self, tmp_path):
        """指定したプロファイル名でセクションを作成し、指定した値が書き込まれる"""
        config_path = tmp_path / "config.toml"

        result = config.create_profile(
            "main",
            redmine_url="https://redmine.example.com",
            redmine_api_key="secret",
            default_project_id="1",
            wiki_project_id="2",
            editor="nvim",
            config_path=config_path,
        )

        assert result.created is True
        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"] == {
            "redmine_url": "https://redmine.example.com",
            "redmine_api_key": "secret",
            "default_project_id": "1",
            "wiki_project_id": "2",
            "editor": "nvim",
        }

    def test_skips_unspecified_keys(self, tmp_path):
        """指定されなかった項目はセクションに書き込まない"""
        config_path = tmp_path / "config.toml"

        config.create_profile(
            "main", redmine_url="https://redmine.example.com", config_path=config_path
        )

        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"] == {"redmine_url": "https://redmine.example.com"}

    def test_creates_parent_directory(self, tmp_path):
        """親ディレクトリが存在しなくても自動作成する"""
        config_path = tmp_path / "nested" / "config.toml"

        config.create_profile("main", config_path=config_path)

        assert config_path.exists()

    def test_preserves_existing_profiles(self, tmp_path):
        """既存プロファイルを保持したまま新しいプロファイルを追記する"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            default_profile = "main"

            [main]
            redmine_url = "https://redmine.example.com/main"
        """)
        )

        config.create_profile(
            "sub",
            redmine_url="https://redmine.example.com/sub",
            config_path=config_path,
        )

        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["default_profile"] == "main"
        assert doc["main"]["redmine_url"] == "https://redmine.example.com/main"
        assert doc["sub"]["redmine_url"] == "https://redmine.example.com/sub"

    def test_returns_false_when_profile_already_exists(self, tmp_path):
        """同名プロファイルが既に存在する場合はFalseを返し、内容を変更しない"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            [main]
            redmine_url = "https://redmine.example.com/original"
        """)
        )

        result = config.create_profile(
            "main",
            redmine_url="https://redmine.example.com/overwrite",
            config_path=config_path,
        )

        assert result.created is False
        assert result.set_as_default is False
        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"]["redmine_url"] == "https://redmine.example.com/original"

    def test_sets_as_default_when_only_profile(self, tmp_path):
        """作成したプロファイルが唯一のプロファイルであればdefault_profileに設定される"""
        config_path = tmp_path / "config.toml"

        result = config.create_profile(
            "main", redmine_url="https://redmine.example.com", config_path=config_path
        )

        assert result.set_as_default is True
        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["default_profile"] == "main"

    def test_keeps_existing_default_when_other_profiles_exist(self, tmp_path):
        """既存プロファイルがある場合はdefault_profileを変更しない"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            default_profile = "main"

            [main]
            redmine_url = "https://redmine.example.com/main"
        """)
        )

        result = config.create_profile(
            "sub",
            redmine_url="https://redmine.example.com/sub",
            config_path=config_path,
        )

        assert result.set_as_default is False
        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["default_profile"] == "main"


class TestLoadToml:
    """load_toml()はconfig_path指定時にそのファイルを読み込む"""

    def test_loads_existing_file(self, tmp_path):
        """指定したパスが存在すれば内容を辞書として返す"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            default_profile = "main"

            [main]
            redmine_url = "https://redmine.example.com"
        """)
        )

        result = config.load_toml(config_path=config_path)

        assert result["default_profile"] == "main"
        assert result["main"]["redmine_url"] == "https://redmine.example.com"

    def test_returns_empty_dict_when_missing(self, tmp_path):
        """指定したパスが存在しない場合は空の辞書を返す"""
        config_path = tmp_path / "missing.toml"

        assert config.load_toml(config_path=config_path) == {}


class TestUpdateConfig:
    """update_config()はconfig_path指定時にそのファイルを更新する"""

    def test_updates_default_profile_value(self, tmp_path):
        """default_profileで指定されたプロファイルのキーを更新する"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            default_profile = "main"

            [main]
            redmine_url = "https://redmine.example.com/old"
        """)
        )

        config.update_config(
            "redmine_url", "https://redmine.example.com/new", config_path=config_path
        )

        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"]["redmine_url"] == "https://redmine.example.com/new"

    def test_updates_specified_profile(self, tmp_path):
        """profile引数で指定したプロファイルを更新する"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            default_profile = "main"

            [main]
            redmine_url = "https://redmine.example.com/main"

            [sub]
            redmine_url = "https://redmine.example.com/sub"
        """)
        )

        config.update_config(
            "redmine_url",
            "https://redmine.example.com/sub-new",
            profile="sub",
            config_path=config_path,
        )

        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"]["redmine_url"] == "https://redmine.example.com/main"
        assert doc["sub"]["redmine_url"] == "https://redmine.example.com/sub-new"

    def test_exits_when_default_profile_missing(self, tmp_path):
        """default_profileもprofile引数もない場合はexit 1する"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            [main]
            redmine_url = "https://redmine.example.com/main"
        """)
        )

        with pytest.raises(SystemExit) as e:
            config.update_config("redmine_url", "v", config_path=config_path)
        assert e.value.code == 1

    def test_exits_when_profile_not_found(self, tmp_path):
        """指定したprofileが存在しない場合はexit 1する"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            [main]
            redmine_url = "https://redmine.example.com/main"
        """)
        )

        with pytest.raises(SystemExit) as e:
            config.update_config(
                "redmine_url", "v", profile="missing", config_path=config_path
            )
        assert e.value.code == 1


class TestSetDefaultProfile:
    """set_default_profile()はconfig_path指定時にそのファイルのdefault_profileを更新する"""

    def test_sets_default_profile(self, tmp_path):
        """既存プロファイルをdefault_profileに設定しTrueを返す"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            [main]
            redmine_url = "https://redmine.example.com/main"

            [sub]
            redmine_url = "https://redmine.example.com/sub"
        """)
        )

        result = config.set_default_profile("sub", config_path=config_path)

        assert result is True
        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["default_profile"] == "sub"

    def test_returns_false_when_profile_not_found(self, tmp_path):
        """指定したプロファイルが存在しない場合はFalseを返し、ファイルを変更しない"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            [main]
            redmine_url = "https://redmine.example.com/main"
        """)
        )

        result = config.set_default_profile("missing", config_path=config_path)

        assert result is False
        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert "default_profile" not in doc


class TestResolveProfileName:
    """resolve_profile_name()はargvの--profileを優先しdefault_profileにfallbackする"""

    def test_returns_default_profile_when_no_cli_flag(self):
        """--profileが無ければdefault_profileを返し、明示フラグはFalse"""
        toml = {"default_profile": "main"}

        name, explicit = config.resolve_profile_name(toml, ["redi", "issue"])

        assert name == "main"
        assert explicit is False

    def test_cli_flag_space_separated_overrides_default(self):
        """`--profile sub`形式のargvがdefault_profileを上書きする"""
        toml = {"default_profile": "main"}

        name, explicit = config.resolve_profile_name(
            toml, ["redi", "--profile", "sub", "issue"]
        )

        assert name == "sub"
        assert explicit is True

    def test_cli_flag_equals_form_overrides_default(self):
        """`--profile=sub`形式のargvがdefault_profileを上書きする"""
        toml = {"default_profile": "main"}

        name, explicit = config.resolve_profile_name(
            toml, ["redi", "--profile=sub", "issue"]
        )

        assert name == "sub"
        assert explicit is True

    def test_returns_none_when_no_default_and_no_flag(self):
        """default_profileもargvも無い場合はNoneを返す"""
        name, explicit = config.resolve_profile_name({}, ["redi", "issue"])

        assert name is None
        assert explicit is False

    def test_does_not_match_default_profile_flag(self):
        """--default_profileは--profileに誤マッチしない"""
        toml = {"default_profile": "main"}

        name, explicit = config.resolve_profile_name(
            toml, ["redi", "config", "update", "--default_profile", "sub"]
        )

        assert name == "main"
        assert explicit is False


class TestShowAllProfiles:
    """show_all_profiles()はconfig_path指定時にそのファイルの全プロファイルを表示する"""

    def test_outputs_all_profiles(self, tmp_path, capsys):
        """複数プロファイルがdefault_profileと共にTOML形式で出力される"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            default_profile = "main"

            [main]
            redmine_url = "https://redmine.example.com/main"
            default_project_id = "1"

            [sub]
            redmine_url = "https://redmine.example.com/sub"
            default_project_id = "2"
        """)
        )

        config.show_all_profiles(config_path=config_path)

        out = capsys.readouterr().out
        doc = tomllib.loads(out)
        assert doc["default_profile"] == "main"
        assert doc["main"]["redmine_url"] == "https://redmine.example.com/main"
        assert doc["sub"]["redmine_url"] == "https://redmine.example.com/sub"

    def test_hides_api_key(self, tmp_path, capsys):
        """APIキーは出力に含まれない"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            [main]
            redmine_url = "https://redmine.example.com/main"
            redmine_api_key = "secret-main"

            [sub]
            redmine_url = "https://redmine.example.com/sub"
            redmine_api_key = "secret-sub"
        """)
        )

        config.show_all_profiles(config_path=config_path)

        out = capsys.readouterr().out
        assert "secret-main" not in out
        assert "secret-sub" not in out
        assert "redmine_api_key" not in out

    def test_prints_message_when_config_missing(self, tmp_path, capsys):
        """config.tomlが存在しない場合はメッセージを出力する"""
        config_path = tmp_path / "missing.toml"

        config.show_all_profiles(config_path=config_path)

        out = capsys.readouterr().out
        assert "not found" in out
