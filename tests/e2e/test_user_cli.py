import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _unique_login(prefix: str) -> str:
    """ユーザー login 用のユニーク文字列(英数のみ)。"""
    # unique_identifier はハイフン区切りなので、login に使えるよう "-" を除く
    return (prefix + unique_identifier("u")).replace("-", "")


def _create_user(login: str, firstname: str = "First", lastname: str = "Last") -> str:
    """user を作成し user_id を返す。"""
    result = run_redi(
        "user",
        "create",
        login,
        "-f",
        firstname,
        "-l",
        lastname,
        "-m",
        f"{login}@example.com",
        "--password",
        "abcdABCD12",
    )
    assert result.returncode == 0, (
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    # 出力例: "Created user: 6 e2etest1 http://localhost:3000/users/6"
    parts = result.stdout.strip().split()
    user_id = parts[2]
    assert user_id.isdigit(), f"想定外の create 出力:\n{result.stdout}"
    return user_id


@pytest.mark.e2e
class TestUserList:
    """`redi user list` はユーザー一覧を表示する"""

    def test_lists_created_user(self):
        """事前 create した login が list に含まれる (create は正しい前提)"""
        login = _unique_login("e2elist")
        user_id = _create_user(login)

        result = run_redi("user", "list")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert login in result.stdout
        assert user_id in result.stdout


@pytest.mark.e2e
class TestUserView:
    """`redi user view <id>` は指定したユーザーの情報を表示する"""

    def test_succeeds_for_created_user(self):
        """create した user を view すると login/mail が含まれる (create は正しい前提)"""
        login = _unique_login("e2eview")
        user_id = _create_user(login)

        result = run_redi("user", "view", user_id)
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert login in result.stdout


@pytest.mark.e2e
class TestUserCreate:
    """`redi user create` は新しいユーザーを作成する"""

    def test_creates_then_view_shows_it(self):
        """create した user が view で取得できる (view は正しい前提)"""
        login = _unique_login("e2ecre")
        user_id = _create_user(login)

        view_result = run_redi("user", "view", user_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert login in view_result.stdout


@pytest.mark.e2e
class TestUserUpdate:
    """`redi user update` は既存のユーザーを更新する"""

    def test_updates_then_view_shows_new_firstname(self):
        """create→update した後 view で更新後の firstname が確認できる (create/view は正しい前提)"""
        login = _unique_login("e2eupd")
        user_id = _create_user(login, firstname="Original")

        update_result = run_redi("user", "update", user_id, "-f", "Updated")
        assert update_result.returncode == 0, (
            f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
        )

        view_result = run_redi("user", "view", user_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert "Updated" in view_result.stdout
        assert "Original" not in view_result.stdout


@pytest.mark.e2e
class TestUserDelete:
    """`redi user delete` は指定したユーザーを削除する"""

    def test_deletes_then_view_fails(self):
        """create→delete した後 view が失敗する (create/view は正しい前提)"""
        login = _unique_login("e2edel")
        user_id = _create_user(login)

        delete_result = run_redi("user", "delete", user_id, "-y")
        assert delete_result.returncode == 0, (
            f"stdout:\n{delete_result.stdout}\nstderr:\n{delete_result.stderr}"
        )

        view_result = run_redi("user", "view", user_id)
        assert view_result.returncode != 0, (
            f"削除後 view が成功してしまった\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert "User not found" in view_result.stdout, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
