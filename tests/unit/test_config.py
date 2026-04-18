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
            redmine_url="https://example.com",
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
            "redmine_url": "https://example.com",
            "redmine_api_key": "secret",
            "default_project_id": "1",
            "wiki_project_id": "2",
            "editor": "nvim",
        }

    def test_skips_unspecified_keys(self, tmp_path):
        """指定されなかった項目はセクションに書き込まない"""
        config_path = tmp_path / "config.toml"

        config.create_profile(
            "main", redmine_url="https://example.com", config_path=config_path
        )

        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"] == {"redmine_url": "https://example.com"}

    def test_creates_parent_directory(self, tmp_path):
        """親ディレクトリが存在しなくても自動作成する"""
        config_path = tmp_path / "nested" / "config.toml"

        config.create_profile("main", config_path=config_path)

        assert config_path.exists()

    def test_preserves_existing_profiles(self, tmp_path):
        """既存プロファイルを保持したまま新しいプロファイルを追記する"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            'default_profile = "main"\n\n[main]\nredmine_url = "https://main"\n'
        )

        config.create_profile("sub", redmine_url="https://sub", config_path=config_path)

        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["default_profile"] == "main"
        assert doc["main"]["redmine_url"] == "https://main"
        assert doc["sub"]["redmine_url"] == "https://sub"

    def test_returns_false_when_profile_already_exists(self, tmp_path):
        """同名プロファイルが既に存在する場合はFalseを返し、内容を変更しない"""
        config_path = tmp_path / "config.toml"
        config_path.write_text('[main]\nredmine_url = "https://original"\n')

        result = config.create_profile(
            "main", redmine_url="https://overwrite", config_path=config_path
        )

        assert result.created is False
        assert result.set_as_default is False
        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"]["redmine_url"] == "https://original"

    def test_sets_as_default_when_only_profile(self, tmp_path):
        """作成したプロファイルが唯一のプロファイルであればdefault_profileに設定される"""
        config_path = tmp_path / "config.toml"

        result = config.create_profile(
            "main", redmine_url="https://example.com", config_path=config_path
        )

        assert result.set_as_default is True
        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["default_profile"] == "main"

    def test_keeps_existing_default_when_other_profiles_exist(self, tmp_path):
        """既存プロファイルがある場合はdefault_profileを変更しない"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            'default_profile = "main"\n\n[main]\nredmine_url = "https://main"\n'
        )

        result = config.create_profile(
            "sub", redmine_url="https://sub", config_path=config_path
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
            'default_profile = "main"\n\n[main]\nredmine_url = "https://example.com"\n'
        )

        result = config.load_toml(config_path=config_path)

        assert result["default_profile"] == "main"
        assert result["main"]["redmine_url"] == "https://example.com"

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
            'default_profile = "main"\n\n[main]\nredmine_url = "https://old"\n'
        )

        config.update_config("redmine_url", "https://new", config_path=config_path)

        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"]["redmine_url"] == "https://new"

    def test_updates_specified_profile(self, tmp_path):
        """profile引数で指定したプロファイルを更新する"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            'default_profile = "main"\n\n[main]\nredmine_url = "https://main"\n\n[sub]\nredmine_url = "https://sub"\n'
        )

        config.update_config(
            "redmine_url", "https://sub-new", profile="sub", config_path=config_path
        )

        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"]["redmine_url"] == "https://main"
        assert doc["sub"]["redmine_url"] == "https://sub-new"

    def test_exits_when_default_profile_missing(self, tmp_path):
        """default_profileもprofile引数もない場合はexit 1する"""
        config_path = tmp_path / "config.toml"
        config_path.write_text('[main]\nredmine_url = "https://main"\n')

        with pytest.raises(SystemExit) as e:
            config.update_config("redmine_url", "v", config_path=config_path)
        assert e.value.code == 1

    def test_exits_when_profile_not_found(self, tmp_path):
        """指定したprofileが存在しない場合はexit 1する"""
        config_path = tmp_path / "config.toml"
        config_path.write_text('[main]\nredmine_url = "https://main"\n')

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
            '[main]\nredmine_url = "https://main"\n\n[sub]\nredmine_url = "https://sub"\n'
        )

        result = config.set_default_profile("sub", config_path=config_path)

        assert result is True
        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["default_profile"] == "sub"

    def test_returns_false_when_profile_not_found(self, tmp_path):
        """指定したプロファイルが存在しない場合はFalseを返し、ファイルを変更しない"""
        config_path = tmp_path / "config.toml"
        config_path.write_text('[main]\nredmine_url = "https://main"\n')

        result = config.set_default_profile("missing", config_path=config_path)

        assert result is False
        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert "default_profile" not in doc
