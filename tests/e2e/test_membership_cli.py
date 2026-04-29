import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _unique_login(prefix: str) -> str:
    return (prefix + unique_identifier("u")).replace("-", "")


def _create_user(login: str) -> str:
    """テスト用 user を作成し user_id を返す。"""
    result = run_redi(
        "user",
        "create",
        login,
        "-f",
        "F",
        "-l",
        "L",
        "-m",
        f"{login}@example.com",
        "--password",
        "abcdABCD12",
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    user_id = result.stdout.strip().split()[2]
    assert user_id.isdigit(), f"想定外の create 出力:\n{result.stdout}"
    return user_id


def _create_membership(user_id: str, role_ids: str = "4") -> str:
    """指定 user で membership を作成し membership_id を返す。

    role_ids 4=開発者 (init-redmine.sh で生成済み)。
    """
    result = run_redi("membership", "create", "-u", user_id, "-r", role_ids)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    # 出力例: "Created membership: 2 [user] 12 F L - 開発者"
    membership_id = result.stdout.strip().split()[2]
    assert membership_id.isdigit(), f"想定外の create 出力:\n{result.stdout}"
    return membership_id


@pytest.mark.e2e
class TestMembershipList:
    """`redi membership list` はメンバーシップ一覧を表示する"""

    def test_lists_created_membership(self):
        """事前 create した membership_id が list に含まれる (create は正しい前提)"""
        user_id = _create_user(_unique_login("mlist"))
        membership_id = _create_membership(user_id)

        result = run_redi("membership", "list")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert membership_id in result.stdout.split("\n")[0] or any(
            line.startswith(f"{membership_id} ") for line in result.stdout.splitlines()
        ), f"membership_id={membership_id} が list に見当たらない\n{result.stdout}"


@pytest.mark.e2e
class TestMembershipView:
    """`redi membership view <id>` は指定したメンバーシップの情報を表示する"""

    def test_succeeds_for_created_membership(self):
        """create した membership を view すると role が含まれる (create は正しい前提)"""
        user_id = _create_user(_unique_login("mview"))
        membership_id = _create_membership(user_id)

        result = run_redi("membership", "view", membership_id)
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "開発者" in result.stdout


@pytest.mark.e2e
class TestMembershipCreate:
    """`redi membership create` は新しいメンバーシップを作成する"""

    def test_creates_then_view_shows_it(self):
        """create した membership が view で取得できる (view は正しい前提)"""
        user_id = _create_user(_unique_login("mcre"))
        membership_id = _create_membership(user_id)

        view_result = run_redi("membership", "view", membership_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )


@pytest.mark.e2e
class TestMembershipUpdate:
    """`redi membership update` は既存のメンバーシップを更新する"""

    def test_updates_then_view_shows_new_roles(self):
        """create→update した後 view で更新後の roles が確認できる (create/view は正しい前提)"""
        user_id = _create_user(_unique_login("mupd"))
        membership_id = _create_membership(user_id, role_ids="4")

        update_result = run_redi("membership", "update", membership_id, "-r", "4,5")
        assert update_result.returncode == 0, (
            f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
        )

        view_result = run_redi("membership", "view", membership_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        # 4=開発者, 5=報告者 が両方含まれること
        assert "開発者" in view_result.stdout
        assert "報告者" in view_result.stdout


@pytest.mark.e2e
class TestMembershipDelete:
    """`redi membership delete` は指定したメンバーシップを削除する"""

    def test_deletes_then_view_fails(self):
        """create→delete した後 view が失敗する (create/view は正しい前提)"""
        user_id = _create_user(_unique_login("mdel"))
        membership_id = _create_membership(user_id)

        delete_result = run_redi("membership", "delete", membership_id, "-y")
        assert delete_result.returncode == 0, (
            f"stdout:\n{delete_result.stdout}\nstderr:\n{delete_result.stderr}"
        )

        view_result = run_redi("membership", "view", membership_id)
        assert view_result.returncode != 0, (
            f"削除後 view が成功してしまった\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert "Membership not found" in view_result.stdout, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
