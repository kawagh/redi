import pytest

from redi import config_schema
from redi.config_schema import Severity


@pytest.fixture(autouse=True)
def clear_env(monkeypatch):
    """環境変数の有無で結果が変わるため、既定では未設定にしておく"""
    for name in config_schema.ENV_FALLBACK.values():
        monkeypatch.delenv(name, raising=False)


def _valid_profile() -> dict:
    return {
        "redmine_url": "https://redmine.example.com",
        "redmine_api_key": "secret",
        "default_project_id": "1",
        "wiki_project_id": "2",
        "editor": "nvim",
        "language": "ja",
    }


def _keys(issues: list) -> list[str | None]:
    return [issue.key for issue in issues]


class TestValidProfile:
    """すべての項目が揃った妥当なプロファイルは問題を報告しない"""

    def test_no_issues(self):
        """妥当なプロファイルでは issue が出ない"""
        assert config_schema.validate_profile("main", _valid_profile()) == []

    def test_optional_keys_are_omittable(self):
        """必須キーだけでも問題にならない"""
        values = {
            "redmine_url": "https://redmine.example.com",
            "redmine_api_key": "secret",
        }
        assert config_schema.validate_profile("main", values) == []


class TestRequiredKeys:
    """redmine_url と redmine_api_key は必須"""

    @pytest.mark.parametrize("key", ["redmine_url", "redmine_api_key"])
    def test_missing_required_key_is_error(self, key):
        """必須キーが無ければ ERROR になる"""
        values = _valid_profile()
        del values[key]

        issues = config_schema.validate_profile("main", values)

        assert _keys(issues) == [key]
        assert issues[0].severity is Severity.ERROR
        assert issues[0].profile == "main"

    @pytest.mark.parametrize(
        ("key", "env_name"),
        [("redmine_url", "REDMINE_URL"), ("redmine_api_key", "REDMINE_API_KEY")],
    )
    def test_missing_required_key_is_warning_when_env_is_set(
        self, key, env_name, monkeypatch
    ):
        """環境変数で補われるなら実行はできるので WARNING に留める

        API キーを config.toml に平文で置かず、シークレット管理ツール経由で
        環境変数として渡す運用を誤検知しないため。
        """
        monkeypatch.setenv(env_name, "from-env")
        values = _valid_profile()
        del values[key]

        issues = config_schema.validate_profile("main", values)

        assert _keys(issues) == [key]
        assert issues[0].severity is Severity.WARNING
        assert env_name in issues[0].message

    def test_empty_required_key_is_error_even_with_env(self, monkeypatch):
        """明示的に空文字を書いている場合は環境変数があっても ERROR"""
        monkeypatch.setenv("REDMINE_API_KEY", "from-env")
        values = _valid_profile() | {"redmine_api_key": ""}

        issues = config_schema.validate_profile("main", values)

        assert _keys(issues) == ["redmine_api_key"]
        assert issues[0].severity is Severity.ERROR


class TestValueChecks:
    """各項目の値を検証する"""

    @pytest.mark.parametrize("url", ["redmine.example.com", "ftp://example.com"])
    def test_url_without_scheme_is_error(self, url):
        """http(s):// で始まらない URL は ERROR"""
        issues = config_schema.validate_profile(
            "main", _valid_profile() | {"redmine_url": url}
        )

        assert _keys(issues) == ["redmine_url"]
        assert issues[0].severity is Severity.ERROR

    def test_non_string_value_is_error(self):
        """文字列であるべき項目に別の型が入っていれば ERROR"""
        issues = config_schema.validate_profile(
            "main", _valid_profile() | {"editor": []}
        )

        assert _keys(issues) == ["editor"]
        assert issues[0].severity is Severity.ERROR

    def test_unknown_language_is_warning(self):
        """未対応の言語コードは en にフォールバックして動くので WARNING"""
        issues = config_schema.validate_profile(
            "main", _valid_profile() | {"language": "jp"}
        )

        assert _keys(issues) == ["language"]
        assert issues[0].severity is Severity.WARNING
        assert "jp" in issues[0].message

    @pytest.mark.parametrize("key", ["default_project_id", "wiki_project_id"])
    def test_integer_project_id_is_warning(self, key):
        """project_id を整数で書いていても動くので WARNING に留める"""
        issues = config_schema.validate_profile("main", _valid_profile() | {key: 1})

        assert _keys(issues) == [key]
        assert issues[0].severity is Severity.WARNING

    @pytest.mark.parametrize("key", ["redmine_url", "language"])
    def test_type_is_checked_before_value(self, key):
        """値の妥当性より先に型を見る(URL や言語コードの判定が壊れないように)"""
        issues = config_schema.validate_profile("main", _valid_profile() | {key: 1})

        assert _keys(issues) == [key]
        assert issues[0].severity is Severity.ERROR

    def test_unknown_key_is_warning(self):
        """未知のキーは将来のキー追加に備えて WARNING に留める"""
        issues = config_schema.validate_profile(
            "main", _valid_profile() | {"redmine_ur": "typo"}
        )

        assert _keys(issues) == ["redmine_ur"]
        assert issues[0].severity is Severity.WARNING


class TestValidateTopLevel:
    """プロファイルに属さないトップレベルの記述を検証する"""

    def test_no_issues(self):
        """default_profile が実在するプロファイルを指していれば問題ない"""
        doc = {"default_profile": "main", "main": _valid_profile()}
        assert config_schema.validate_top_level(doc) == []

    def test_default_profile_pointing_to_missing_profile_is_error(self):
        """default_profile が実在しないプロファイルを指していれば ERROR"""
        doc = {"default_profile": "sub", "main": _valid_profile()}

        issues = config_schema.validate_top_level(doc)

        assert _keys(issues) == ["default_profile"]
        assert issues[0].severity is Severity.ERROR
        assert issues[0].profile is None
        assert "sub" in issues[0].message

    def test_non_string_default_profile_is_error(self):
        """default_profile が文字列でなければ ERROR"""
        doc = {"default_profile": 1, "main": _valid_profile()}

        issues = config_schema.validate_top_level(doc)

        assert _keys(issues) == ["default_profile"]
        assert issues[0].severity is Severity.ERROR

    def test_key_outside_profile_is_warning(self):
        """テーブルより前に書かれたキーはどのプロファイルにも属さないので WARNING"""
        doc = {
            "redmine_url": "https://redmine.example.com",
            "default_profile": "main",
            "main": _valid_profile(),
        }

        issues = config_schema.validate_top_level(doc)

        assert _keys(issues) == ["redmine_url"]
        assert issues[0].severity is Severity.WARNING

    def test_ignores_profile_tables(self):
        """プロファイルのテーブル自体はトップレベルの問題として扱わない"""
        doc = {"main": _valid_profile(), "sub": _valid_profile()}
        assert config_schema.validate_top_level(doc) == []


class TestHelpers:
    """検証結果を扱うヘルパ"""

    def test_profile_names_of_returns_table_keys(self):
        """テーブルとして書かれたキーだけをプロファイル名として返す"""
        doc = {"default_profile": "main", "main": {}, "sub": {}}
        assert config_schema.profile_names_of(doc) == ["main", "sub"]

    def test_has_error_is_false_for_warnings_only(self):
        """WARNING だけなら has_error は False"""
        issues = config_schema.validate_profile(
            "main", _valid_profile() | {"language": "jp"}
        )
        assert config_schema.has_error(issues) is False

    def test_has_error_is_true_for_errors(self):
        """ERROR が混ざれば has_error は True"""
        values = _valid_profile()
        del values["redmine_api_key"]
        assert (
            config_schema.has_error(config_schema.validate_profile("main", values))
            is True
        )

    def test_credentials_of_prefers_profile(self, monkeypatch):
        """プロファイルに値があれば環境変数より優先する"""
        monkeypatch.setenv("REDMINE_URL", "https://other.example.com")

        assert config_schema.credentials_of(_valid_profile()) == (
            "https://redmine.example.com",
            "secret",
        )

    def test_credentials_of_falls_back_to_env(self, monkeypatch):
        """プロファイルに無い必須キーは環境変数で補う"""
        monkeypatch.setenv("REDMINE_API_KEY", "from-env")
        values = _valid_profile()
        del values["redmine_api_key"]

        assert config_schema.credentials_of(values) == (
            "https://redmine.example.com",
            "from-env",
        )

    def test_credentials_of_returns_none_when_unresolved(self):
        """どちらにも無ければ None"""
        values = _valid_profile()
        del values["redmine_api_key"]

        assert config_schema.credentials_of(values) is None

    def test_credentials_of_returns_none_for_non_string(self):
        """文字列でない値は接続先として使えない"""
        assert (
            config_schema.credentials_of(_valid_profile() | {"redmine_url": 1}) is None
        )

    def test_active_env_overrides_lists_set_variables(self, monkeypatch):
        """設定されている環境変数だけを返す"""
        monkeypatch.setenv("REDMINE_URL", "https://redmine.example.com")
        assert config_schema.active_env_overrides() == ["REDMINE_URL"]

    def test_active_env_overrides_is_empty_when_unset(self):
        """環境変数が無ければ空リスト"""
        assert config_schema.active_env_overrides() == []
