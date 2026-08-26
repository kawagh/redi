import json

import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_user(login: str) -> str:
    """ユーザーを作成して id を返す。"""
    run_redi(
        "user",
        "create",
        login,
        "--firstname",
        "e2e",
        "--lastname",
        "user",
        "--mail",
        f"{login}@example.com",
        "--generate_password",
    )
    for user in json.loads(run_redi("user", "list", "--full").stdout):
        if user["login"] == login:
            return str(user["id"])
    raise AssertionError(f"作成したユーザーが一覧に無い: {login}")


def _logins(*args: str) -> list[str]:
    """`user list` のフィルタ結果を login のリストで返す。"""
    listed = json.loads(run_redi("user", "list", *args, "--full").stdout)
    return [user["login"] for user in listed]


@pytest.mark.e2e
class TestUserListFilter:
    """`redi user list` はフィルタ条件に合うユーザーだけを返す"""

    def test_name_matches_partially(self):
        """--name はログイン名への部分一致で絞り込む"""
        login = unique_identifier("e2e-user-name")
        _create_user(login)

        assert _logins("--name", login) == [login]

    def test_status_selects_target_status(self):
        """--status は指定したステータスのユーザーだけを返す"""
        login = unique_identifier("e2e-user-status")
        _create_user(login)

        assert login in _logins("--status", "active")
        assert login not in _logins("--status", "locked")

    def test_group_id_selects_members(self):
        """--group_id は指定したグループの所属ユーザーだけを返す"""
        login = unique_identifier("e2e-user-group")
        user_id = _create_user(login)
        group_name = unique_identifier("e2e-user-group-owner")
        run_redi("group", "create", group_name)
        group_id = next(
            str(group["id"])
            for group in json.loads(run_redi("group", "list", "--full").stdout)
            if group["name"] == group_name
        )
        run_redi("group", "update", group_id, "--add-user", user_id)

        assert _logins("--group_id", group_id) == [login]
