import pytest

from tests.e2e.utils import run_redi


@pytest.mark.e2e
class TestRoleList:
    """`redi role list` はロール一覧を表示する"""

    def test_lists_default_roles(self):
        """init-redmine.sh で読み込まれた既定ロール(管理者/開発者/報告者)が出力に含まれる"""
        result = run_redi("role", "list")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        for name in ("管理者", "開発者", "報告者"):
            assert name in result.stdout, (
                f"既定のロール '{name}' が出力に見当たらない\n{result.stdout}"
            )


@pytest.mark.e2e
class TestRoleView:
    """`redi role view <id>` は指定したロールの情報を表示する"""

    def test_succeeds_for_existing_role(self):
        """init-redmine.sh で作成された id=4(開発者)を view すると exit 0 で成功する"""
        result = run_redi("role", "view", "4")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "開発者" in result.stdout

    def test_fails_for_nonexistent_role(self):
        """存在しないロール id を view するとエラーになる"""
        result = run_redi("role", "view", "999999")
        assert result.returncode != 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "Role not found" in result.stdout, (
            f"想定外のエラー\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
