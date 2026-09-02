import textwrap
import tomllib
from pathlib import Path

import pytest

from redi import config


class TestResolveConfigPath:
    """config.tomlの場所は環境変数REDI_CONFIG_PATHで差し替えられる"""

    def test_defaults_to_user_config(self):
        """未設定なら~/.config/redi/config.tomlを使う"""
        assert config.resolve_config_path({}) == config.DEFAULT_CONFIG_PATH

    def test_empty_value_falls_back_to_default(self):
        """空文字は未設定と同じ扱いにし、意図せず相対パスを掴まないようにする"""
        assert (
            config.resolve_config_path({"REDI_CONFIG_PATH": ""})
            == config.DEFAULT_CONFIG_PATH
        )

    def test_uses_given_path(self):
        """指定されたパスをそのまま使う"""
        assert config.resolve_config_path(
            {"REDI_CONFIG_PATH": "/tmp/redi/config.toml"}
        ) == Path("/tmp/redi/config.toml")

    def test_expands_home(self):
        """シェルを介さず渡されても~を展開する"""
        assert (
            config.resolve_config_path({"REDI_CONFIG_PATH": "~/e2e/config.toml"})
            == Path.home() / "e2e" / "config.toml"
        )


class TestProfile:
    """Profileはconfig.tomlの1プロファイル分の設定値を表す"""

    def test_from_dict_takes_known_keys(self):
        """Profileが持つキーだけを取り込み、TOMLの数値は文字列に正規化する"""
        profile = config.Profile.from_dict(
            {
                "redmine_url": "https://redmine.example.com",
                "default_project_id": 42,
                "unknown": "x",
            }
        )

        assert profile == config.Profile(
            redmine_url="https://redmine.example.com", default_project_id="42"
        )

    def test_from_dict_treats_empty_value_as_unset(self):
        """falsyな値は未設定とみなす"""
        assert config.Profile.from_dict({"editor": ""}).editor is None

    def test_to_dict_omits_unset(self):
        """未設定の項目はconfig.tomlに空値を残さないようキーごと省く"""
        profile = config.Profile(redmine_url="https://redmine.example.com")

        assert profile.to_dict() == {"redmine_url": "https://redmine.example.com"}

    def test_merge_overlays_set_values_only(self):
        """設定済みの項目だけが上書きされる"""
        base = config.Profile(redmine_url="https://base.example.com", editor="vim")

        merged = base.merge(config.Profile(editor="nvim"))

        assert merged == config.Profile(
            redmine_url="https://base.example.com", editor="nvim"
        )


class TestCreateProfile:
    """create_profile()はconfig.tomlに新しいプロファイルセクションを追加する"""

    def test_creates_new_profile_section(self, tmp_path):
        """指定したプロファイル名でセクションを作成し、指定した値が書き込まれる"""
        config_path = tmp_path / "config.toml"

        result = config.create_profile(
            "main",
            config.Profile(
                redmine_url="https://redmine.example.com",
                redmine_api_key="secret",
                default_project_id="1",
                wiki_project_id="2",
                editor="nvim",
                language="ja",
            ),
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
            "language": "ja",
        }

    def test_skips_unspecified_keys(self, tmp_path):
        """指定されなかった項目はセクションに書き込まない"""
        config_path = tmp_path / "config.toml"

        config.create_profile(
            "main",
            config.Profile(redmine_url="https://redmine.example.com"),
            config_path=config_path,
        )

        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"] == {"redmine_url": "https://redmine.example.com"}

    def test_creates_parent_directory(self, tmp_path):
        """親ディレクトリが存在しなくても自動作成する"""
        config_path = tmp_path / "nested" / "config.toml"

        config.create_profile("main", config.Profile(), config_path=config_path)

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
            config.Profile(redmine_url="https://redmine.example.com/sub"),
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
            config.Profile(redmine_url="https://redmine.example.com/overwrite"),
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
            "main",
            config.Profile(redmine_url="https://redmine.example.com"),
            config_path=config_path,
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
            config.Profile(redmine_url="https://redmine.example.com/sub"),
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


class TestUpdateProfile:
    """update_profile()はconfig_path指定時にそのファイルを更新する"""

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

        config.update_profile(
            config.Profile(redmine_url="https://redmine.example.com/new"),
            config_path=config_path,
        )

        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"]["redmine_url"] == "https://redmine.example.com/new"

    def test_updates_multiple_keys(self, tmp_path):
        """設定済みの項目をまとめて更新する"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            default_profile = "main"

            [main]
            redmine_url = "https://redmine.example.com"
            language = "en"
        """)
        )

        config.update_profile(
            config.Profile(language="ja", editor="nvim"), config_path=config_path
        )

        with open(config_path, "rb") as f:
            doc = tomllib.load(f)
        assert doc["main"]["language"] == "ja"
        assert doc["main"]["editor"] == "nvim"

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

        config.update_profile(
            config.Profile(redmine_url="https://redmine.example.com/sub-new"),
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
            config.update_profile(
                config.Profile(redmine_url="v"), config_path=config_path
            )
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
            config.update_profile(
                config.Profile(redmine_url="v"),
                profile="missing",
                config_path=config_path,
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


class TestListProfileNames:
    """list_profile_names()はconfig.tomlの[section]名一覧を返す"""

    def test_returns_profile_names_in_file_order(self, tmp_path):
        """テーブルセクションの名前のみをファイル記載順で返す"""
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

        assert config.list_profile_names(config_path=config_path) == ["main", "sub"]

    def test_returns_empty_list_when_missing(self, tmp_path):
        """ファイルが存在しない場合は空リストを返す"""
        assert config.list_profile_names(config_path=tmp_path / "missing.toml") == []


class TestGetDefaultProfile:
    """get_default_profile()はconfig.tomlのdefault_profileを返す"""

    def test_returns_default_profile_value(self, tmp_path):
        """default_profileの値を文字列で返す"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            default_profile = "main"

            [main]
            redmine_url = "https://redmine.example.com"
        """)
        )

        assert config.get_default_profile(config_path=config_path) == "main"

    def test_returns_none_when_unset(self, tmp_path):
        """default_profileが設定されていない場合はNoneを返す"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            [main]
            redmine_url = "https://redmine.example.com"
        """)
        )

        assert config.get_default_profile(config_path=config_path) is None

    def test_returns_none_when_file_missing(self, tmp_path):
        """ファイルが存在しない場合はNoneを返す"""
        assert config.get_default_profile(config_path=tmp_path / "missing.toml") is None


class TestReadProfile:
    """read_profile()は指定プロファイルに書かれている設定値をProfileで返す"""

    def test_returns_written_values(self, tmp_path):
        """書かれていない項目は未設定のままで、デフォルト値は補わない"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            default_profile = "main"

            [main]
            redmine_url = "https://redmine.example.com"
            default_project_id = 42
        """)
        )

        assert config.read_profile("main", config_path=config_path) == config.Profile(
            redmine_url="https://redmine.example.com", default_project_id="42"
        )

    def test_returns_empty_profile_when_profile_missing(self, tmp_path):
        """プロファイルが存在しない場合は全項目が未設定のProfileを返す"""
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            textwrap.dedent("""\
            [main]
            redmine_url = "https://redmine.example.com"
        """)
        )

        assert config.read_profile("sub", config_path=config_path) == config.Profile()

    def test_returns_empty_profile_when_file_missing(self, tmp_path):
        """ファイルが存在しない場合は全項目が未設定のProfileを返す"""
        assert (
            config.read_profile("main", config_path=tmp_path / "x.toml")
            == config.Profile()
        )


class TestShowConfig:
    """show_config()は現在参照しているプロファイルが分かる形で設定値を表示する"""

    def test_outputs_current_profile_as_default(self, monkeypatch, capsys):
        """config.tomlと同じ`[profile_name]`の見出しで出し、既定であることを添える"""
        monkeypatch.setattr(config, "current_profile", "main")
        monkeypatch.setattr(config.sys, "argv", ["redi", "config"])

        config.show_config()

        out = capsys.readouterr().out
        assert out.splitlines()[0].startswith("[main]")
        assert "--profile" not in out

    def test_marks_profile_overridden_by_option(self, monkeypatch, capsys):
        """--profile での一時上書きは既定と区別できる表記になる"""
        monkeypatch.setattr(config, "current_profile", "sub")
        monkeypatch.setattr(config.sys, "argv", ["redi", "--profile", "sub", "config"])

        config.show_config()

        out = capsys.readouterr().out
        assert out.splitlines()[0].startswith("[sub]")
        assert "--profile" in out.splitlines()[0]

    def test_output_is_valid_toml(self, monkeypatch, capsys):
        """見出しを足してもTOMLとして読める(由来はコメントで添える)"""
        monkeypatch.setattr(config, "current_profile", "main")
        monkeypatch.setattr(config.sys, "argv", ["redi", "--profile=main", "config"])
        monkeypatch.setattr(config, "editor", "nvim")

        config.show_config()

        doc = tomllib.loads(capsys.readouterr().out)
        assert doc["main"]["editor"] == "nvim"

    def test_omits_heading_when_profile_is_unknown(self, monkeypatch, capsys):
        """プロファイルが決まっていない場合は見出し無しで設定値だけ出す"""
        monkeypatch.setattr(config, "current_profile", None)
        monkeypatch.setattr(config, "editor", "nvim")

        config.show_config()

        doc = tomllib.loads(capsys.readouterr().out)
        assert doc["editor"] == "nvim"


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

    def test_shows_current_profile(self, tmp_path, monkeypatch, capsys):
        """default_profileとは別に、今回使われたプロファイルが分かる"""
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
        monkeypatch.setattr(config, "current_profile", "sub")
        monkeypatch.setattr(config.sys, "argv", ["redi", "--profile", "sub", "config"])

        config.show_all_profiles(config_path=config_path)

        out = capsys.readouterr().out
        heading = next(line for line in out.splitlines() if line.startswith("[sub]"))
        assert "--profile" in heading
        assert "[main]" in out
        # 見出しにコメントを足してもTOMLとして読めるまま
        assert tomllib.loads(out)["default_profile"] == "main"

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

        err = capsys.readouterr().err
        assert "not found" in err


@pytest.fixture
def no_redmine_env(monkeypatch):
    """環境変数がプロファイルより優先されるため、既定では取り除いておく。"""
    for name in ("REDMINE_URL", "REDMINE_API_KEY", "REDI_EDITOR"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def two_profiles(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        textwrap.dedent("""\
        default_profile = "main"

        [main]
        redmine_url = "https://main.example.com"
        redmine_api_key = "secret-main"
        default_project_id = "10"
        editor = "nvim"
        language = "ja"

        [sub]
        redmine_url = "https://sub.example.com"
        redmine_api_key = "secret-sub"

        [broken]
        redmine_url = "https://broken.example.com"
    """)
    )
    return config_path


class TestResolveMergedConfig:
    """resolve_merged_config()はデフォルト<プロファイル<環境変数の順にマージする"""

    def test_applies_profile_values(self, two_profiles, no_redmine_env):
        """指定したプロファイルの値が反映される"""
        merged = config.resolve_merged_config("main", config.load_toml(two_profiles))

        assert merged.redmine_url == "https://main.example.com"
        assert merged.redmine_api_key == "secret-main"
        assert merged.default_project_id == "10"
        assert merged.editor == "nvim"
        assert merged.language == "ja"

    def test_falls_back_to_defaults(self, two_profiles, no_redmine_env):
        """プロファイルに無い項目はデフォルト値になる"""
        merged = config.resolve_merged_config("sub", config.load_toml(two_profiles))

        assert merged.editor == "vim"
        assert merged.language == "en"
        assert merged.default_project_id is None

    def test_env_overrides_profile(self, two_profiles, monkeypatch):
        """環境変数はプロファイルより優先される"""
        monkeypatch.setenv("REDMINE_URL", "https://env.example.com")

        merged = config.resolve_merged_config("main", config.load_toml(two_profiles))

        assert merged.redmine_url == "https://env.example.com"

    def test_does_not_leak_between_calls(self, two_profiles, no_redmine_env):
        """前回の呼び出しの値が次の呼び出しに残らない

        マージ結果を使い回すと main の値が sub に漏れてしまう。
        """
        config.resolve_merged_config("main", config.load_toml(two_profiles))
        merged = config.resolve_merged_config("sub", config.load_toml(two_profiles))

        assert merged.redmine_url == "https://sub.example.com"
        assert merged.editor == "vim"
        assert merged.default_project_id is None


@pytest.fixture
def restore_config():
    """apply_profile() は設定値のグローバルを書き換えるので、テスト後に元へ戻す"""
    original_profile = config.current_profile
    yield
    config.apply_profile(original_profile)


@pytest.mark.usefixtures("restore_config")
class TestApplyProfile:
    """apply_profile()は実行中のプロファイルを切り替える"""

    def test_rebinds_config_globals(self, two_profiles, no_redmine_env):
        """設定値のグローバルと現在プロファイル名が切替先のものになる"""
        config.apply_profile("sub", config_path=two_profiles)

        assert config.current_profile == "sub"
        assert config.redmine_url == "https://sub.example.com"
        assert config.redmine_api_key == "secret-sub"

    def test_clears_previous_profile_values(self, two_profiles, no_redmine_env):
        """前のプロファイルにしか無い項目は切替後に残らない"""
        config.apply_profile("main", config_path=two_profiles)
        config.apply_profile("sub", config_path=two_profiles)

        assert config.default_project_id is None
        assert config.editor == "vim"


@pytest.fixture
def text_formatting_config(tmp_path):
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        textwrap.dedent("""\
        default_profile = "main"
        text_formatting = "textile"

        [main]
        redmine_url = "https://main.example.com"
        redmine_api_key = "secret-main"

        [md]
        redmine_url = "https://md.example.com"
        redmine_api_key = "secret-md"
        text_formatting = "markdown"
    """)
    )
    return config_path


class TestTextFormatting:
    """text_formattingはRedmineの記法をエージェントが投稿前に参照するための設定

    サーバー側の設定でREST APIからは取得できないため、ユーザーがconfig.tomlに書き、
    `redi config` / `redi config --full` で参照する。
    """

    def test_top_level_is_default_for_all_profiles(
        self, text_formatting_config, no_redmine_env
    ):
        """トップレベルの値は、項目を持たないプロファイルの既定になる"""
        merged = config.resolve_merged_config(
            "main", config.load_toml(text_formatting_config)
        )

        assert merged.text_formatting == "textile"

    def test_profile_overrides_top_level(self, text_formatting_config, no_redmine_env):
        """プロファイル内の値はトップレベルより優先される"""
        merged = config.resolve_merged_config(
            "md", config.load_toml(text_formatting_config)
        )

        assert merged.text_formatting == "markdown"

    def test_defaults_to_markdown(self, two_profiles, no_redmine_env):
        """どちらにも無ければRedmineの新規インストール既定に合わせてmarkdown"""
        merged = config.resolve_merged_config("main", config.load_toml(two_profiles))

        assert merged.text_formatting == "markdown"

    def test_show_config_includes_resolved_value(
        self, text_formatting_config, no_redmine_env, monkeypatch, capsys
    ):
        """`redi config` はトップレベルから引き継いだ値も含めて表示する"""
        monkeypatch.setattr(config.sys, "argv", ["redi", "config"])
        original_profile = config.current_profile
        config.apply_profile("main", config_path=text_formatting_config)
        try:
            config.show_config()
        finally:
            config.apply_profile(original_profile)

        doc = tomllib.loads(capsys.readouterr().out)
        assert doc["main"]["text_formatting"] == "textile"

    def test_show_all_profiles_keeps_top_level_value(
        self, text_formatting_config, capsys
    ):
        """`redi config --full` はトップレベルの値とプロファイルの上書きを両方出す"""
        config.show_all_profiles(config_path=text_formatting_config)

        doc = tomllib.loads(capsys.readouterr().out)
        assert doc["text_formatting"] == "textile"
        assert doc["md"]["text_formatting"] == "markdown"
        assert "text_formatting" not in doc["main"]


class TestProfileHasCredentials:
    """profile_has_credentials()は切替先として使えるプロファイルかを判定する"""

    def test_true_when_url_and_key_are_present(self, two_profiles, no_redmine_env):
        """redmine_urlとredmine_api_keyが揃っていればTrue"""
        assert config.profile_has_credentials("main", config_path=two_profiles) is True

    def test_false_when_api_key_is_missing(self, two_profiles, no_redmine_env):
        """redmine_api_keyが無ければFalse"""
        assert (
            config.profile_has_credentials("broken", config_path=two_profiles) is False
        )

    def test_false_for_unknown_profile(self, two_profiles, no_redmine_env):
        """存在しないプロファイル名ならFalse"""
        assert (
            config.profile_has_credentials("missing", config_path=two_profiles) is False
        )
