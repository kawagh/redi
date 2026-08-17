from types import SimpleNamespace

import pytest

from redi import config
from redi.service import user_service


@pytest.fixture
def stub_user_api(monkeypatch):
    """api.user の取得系を差し替え、渡った引数を記録する。

    fetch_user の include は `calls` に、fetch_users のフィルタは `list_calls` に入る。
    Redmine は管理者で取得したときだけ `api_key` を返すため、スタブは常に含めて返す。
    """

    calls: list[dict] = []
    list_calls: list[dict] = []

    def fake_fetch_users(status=None, name=None, group_id=None):
        list_calls.append({"status": status, "name": name, "group_id": group_id})
        return [
            {"id": 1, "login": "admin", "api_key": "secret1"},
            {"id": 2, "login": "member", "api_key": "secret2"},
        ]

    def fake_fetch_user(user_id, include=None):
        calls.append({"user_id": user_id, "include": include})
        return {"id": int(user_id), "login": "member", "api_key": "secret"}

    def fake_create_user(**kwargs):
        return {"id": 3, "login": kwargs["login"], "api_key": "secret3"}

    monkeypatch.setattr(user_service.user_api, "fetch_users", fake_fetch_users)
    monkeypatch.setattr(user_service.user_api, "fetch_user", fake_fetch_user)
    monkeypatch.setattr(user_service.user_api, "create_user", fake_create_user)
    return SimpleNamespace(calls=calls, list_calls=list_calls)


class TestApiKey:
    """取得結果から API キーを落とす"""

    def test_list_users_drops_apikey(self, stub_user_api):
        """一覧の各ユーザーから api_key を落とす"""
        users = user_service.list_users()

        assert users == [
            {"id": 1, "login": "admin"},
            {"id": 2, "login": "member"},
        ]

    def test_read_user_drops_apikey(self, stub_user_api):
        """詳細から api_key を落とす"""
        assert user_service.read_user("2") == {"id": 2, "login": "member"}

    def test_create_user_drops_apikey(self, stub_user_api):
        """作成結果から api_key を落とす"""
        created = user_service.create_user(
            login="new", firstname="姓", lastname="名", mail="new@example.com"
        )

        assert created == {"id": 3, "login": "new"}


class TestListUsers:
    """list_users がフィルタを API に渡す範囲"""

    def test_no_filter_passes_nothing(self, stub_user_api):
        """フィルタ未指定なら API にも渡さず、Redmine の既定 (active のみ) に任せる"""
        user_service.list_users()

        assert stub_user_api.list_calls == [
            {"status": None, "name": None, "group_id": None}
        ]

    @pytest.mark.parametrize(
        ("status", "expected"),
        [("active", 1), ("registered", 2), ("locked", 3)],
    )
    def test_status_is_mapped_to_api_number(self, stub_user_api, status, expected):
        """status の名前を Redmine が定める数値に変換して渡す"""
        user_service.list_users(status=status)

        assert stub_user_api.list_calls[0]["status"] == expected

    def test_name_and_group_id_are_passed_through(self, stub_user_api):
        """name と group_id はそのまま渡す"""
        user_service.list_users(name="kawagh", group_id=6)

        assert stub_user_api.list_calls == [
            {"status": None, "name": "kawagh", "group_id": 6}
        ]


class TestReadUser:
    """read_user が取得する範囲"""

    def test_detail_includes_memberships_and_groups(self, stub_user_api):
        """detail=True では所属プロジェクトとグループも併せて取得する"""
        user_service.read_user("2", detail=True)

        assert stub_user_api.calls == [
            {"user_id": "2", "include": ["memberships", "groups"]}
        ]

    def test_default_does_not_include(self, stub_user_api):
        """既定では include を指定しない"""
        user_service.read_user("2")

        assert stub_user_api.calls == [{"user_id": "2", "include": None}]


class TestUserUrl:
    """user_url が組み立てる URL"""

    @pytest.fixture(autouse=True)
    def redmine_url(self, monkeypatch):
        monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")

    def test_builds_url(self):
        """ユーザー id から Web UI の URL を組み立てる"""
        assert user_service.user_url(2) == "http://localhost:3001/users/2"
