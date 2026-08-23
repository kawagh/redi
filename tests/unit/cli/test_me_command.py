import json

import pytest

from redi.cli import me_command

ACCOUNT = {
    "id": 1,
    "login": "admin",
    "firstname": "太郎",
    "lastname": "redmine",
    "mail": "admin@example.com",
    "created_on": "2026-01-01T00:00:00Z",
}

USER = {
    **ACCOUNT,
    "admin": True,
    "memberships": [
        {
            "id": 1,
            "project": {"id": 3, "name": "redi"},
            "roles": [{"id": 4, "name": "開発者"}],
        }
    ],
}


@pytest.fixture
def stub_me_service(monkeypatch):
    """取得を固定し、更新の呼び出しを記録する"""
    updates: list[dict] = []
    monkeypatch.setattr(me_command.me_service, "read_my_account", lambda: ACCOUNT)
    monkeypatch.setattr(me_command.me_service, "read_my_user", lambda: USER)
    monkeypatch.setattr(
        me_command.me_service,
        "update_my_account",
        lambda **kwargs: updates.append(kwargs),
    )
    return updates


class TestViewMyAccount:
    """`redi me` の標準出力"""

    def test_prints_memberships(self, stub_me_service, capsys):
        """自分の情報を見るコマンドなので、既定では所属プロジェクトも出す"""
        me_command.view_my_account()

        assert "    3 redi - 開発者" in capsys.readouterr().out.splitlines()

    def test_full_prints_json(self, stub_me_service, capsys):
        """--full では /my/account.json で取得した JSON だけを出す"""
        me_command.view_my_account(full=True)

        assert json.loads(capsys.readouterr().out) == ACCOUNT


class TestUpdateMyAccount:
    """`redi me update` の更新内容の扱い"""

    def test_updates_given_fields_only(self, stub_me_service):
        """指定のない項目は None のまま渡し、更新対象から外す"""
        me_command.update_my_account(firstname="次郎")

        assert stub_me_service == [
            {"firstname": "次郎", "lastname": None, "mail": None}
        ]

    def test_no_changes_exits_without_update(self, stub_me_service, capsys):
        """更新内容がなければ API を呼ばず exit 1 する"""
        with pytest.raises(SystemExit) as e:
            me_command.update_my_account()

        assert e.value.code == 1
        assert stub_me_service == []
        assert capsys.readouterr().out.strip() != ""
