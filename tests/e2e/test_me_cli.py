import pytest

from tests.e2e.utils import run_redi


@pytest.mark.e2e
class TestMe:
    """`redi me` は現在のユーザー情報を表示する"""

    def test_shows_current_user_info(self):
        """init-redmine.sh で sandbox_admin プロファイルが admin に紐付いており、admin の情報が表示される"""
        result = run_redi("me")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "admin" in result.stdout
        assert "admin@example.net" in result.stdout


@pytest.mark.e2e
class TestMeUpdate:
    """`redi me update` は現在のユーザー情報を更新する"""

    def test_updates_firstname_then_view_reflects_it(self):
        """firstname を更新した後 me 表示で更新後の firstname が確認でき、再度元に戻せる"""
        original_firstname = "Redmine"
        new_firstname = "Redmine2"

        update_result = run_redi("me", "update", "-f", new_firstname)
        assert update_result.returncode == 0, (
            f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
        )

        try:
            view_result = run_redi("me")
            assert view_result.returncode == 0, (
                f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
            )
            assert new_firstname in view_result.stdout
        finally:
            # 後続テストのため firstname を元に戻す
            restore = run_redi("me", "update", "-f", original_firstname)
            assert restore.returncode == 0, (
                f"firstname の復元に失敗\nstdout:\n{restore.stdout}\nstderr:\n{restore.stderr}"
            )
