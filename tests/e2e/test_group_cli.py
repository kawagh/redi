import json
import subprocess

import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_group(name: str) -> str:
    """グループを作成して id を返す。"""
    run_redi("group", "create", name)
    for group in json.loads(run_redi("group", "list", "--full").stdout):
        if group["name"] == name:
            return str(group["id"])
    raise AssertionError(f"作成したグループが一覧に無い: {name}")


def _first_user_id() -> str:
    """既存ユーザーの id を1件返す。"""
    users = json.loads(run_redi("user", "list", "--full").stdout)
    return str(users[0]["id"])


def _lists_user(group_id: str, user_id: str) -> bool:
    """`group view` の所属ユーザー行に user_id があるか。

    id だけの部分一致ではグループ名などに紛れるため、行頭で突き合わせる。
    """
    viewed = run_redi("group", "view", group_id).stdout
    return any(line.startswith(f"  {user_id} ") for line in viewed.splitlines())


@pytest.mark.e2e
class TestGroupView:
    """`redi group view` はグループの詳細を表示する"""

    def test_shows_id_and_name(self):
        """作成したグループの id と名前が出る"""
        name = unique_identifier("e2e-group-view")
        group_id = _create_group(name)

        viewed = run_redi("group", "view", group_id).stdout

        assert group_id in viewed
        assert name in viewed


@pytest.mark.e2e
class TestGroupUpdate:
    """`redi group update` はグループを更新する"""

    def test_updated_name_is_reflected(self):
        """更新した名前が詳細表示に反映される"""
        group_id = _create_group(unique_identifier("e2e-group-update"))
        updated_name = unique_identifier("e2e-group-updated")

        run_redi("group", "update", group_id, "--name", updated_name)

        assert updated_name in run_redi("group", "view", group_id).stdout


@pytest.mark.e2e
class TestGroupUser:
    """`redi group update` はグループのユーザーを追加・削除する"""

    def test_added_user_appears_and_disappears(self):
        """追加したユーザーは詳細表示に出て、削除すると出なくなる"""
        group_id = _create_group(unique_identifier("e2e-group-user"))
        user_id = _first_user_id()

        run_redi("group", "update", group_id, "--add-user", user_id)
        assert _lists_user(group_id, user_id)

        run_redi("group", "update", group_id, "--remove-user", user_id)
        assert not _lists_user(group_id, user_id)


@pytest.mark.e2e
class TestGroupDelete:
    """`redi group delete` はグループを削除する"""

    def test_deleted_group_disappears_from_list(self):
        """削除したグループは一覧に出てこなくなる"""
        name = unique_identifier("e2e-group-delete")
        group_id = _create_group(name)

        run_redi("group", "delete", group_id, "--yes")

        assert name not in run_redi("group", "list").stdout

    def test_exits_with_error_for_missing_group(self):
        """存在しないグループの削除は exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("group", "delete", "999999", "--yes")

        assert e.value.returncode == 1
