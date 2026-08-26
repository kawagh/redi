import pytest

from redi import config
from redi.service import version_service


class TestVersionUrl:
    def test_builds_url_from_redmine_url(self, monkeypatch):
        """Redmine の URL に /versions/{id} を繋いだ URL を返す"""
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")

        assert version_service.version_url(42) == "http://localhost:3001/versions/42"


class TestHasUpdateFields:
    """更新項目が指定されているかの判定"""

    def test_no_fields(self):
        """何も指定されていなければ False"""
        assert version_service.has_update_fields() is False

    @pytest.mark.parametrize(
        "field",
        ["name", "status", "sharing"],
    )
    def test_empty_string_is_not_update(self, field):
        """name / status / sharing の空文字は値を消せないので指定なし扱い"""
        assert version_service.has_update_fields(**{field: ""}) is False

    @pytest.mark.parametrize("field", ["due_date", "description"])
    def test_empty_string_clears_value(self, field):
        """due_date / description の空文字は値を消す指定として扱う"""
        assert version_service.has_update_fields(**{field: ""}) is True
