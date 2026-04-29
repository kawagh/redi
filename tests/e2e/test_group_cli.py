import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_group(name: str) -> str:
    """group を作成し group_id を返す。"""
    result = run_redi("group", "create", name)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    # 出力例: "Created group: 18 test-group-1 http://localhost:3000/groups/18"
    group_id = result.stdout.strip().split()[2]
    assert group_id.isdigit(), f"想定外の create 出力:\n{result.stdout}"
    return group_id


@pytest.mark.e2e
class TestGroupList:
    """`redi group list` はグループ一覧を表示する"""

    def test_lists_created_group(self):
        """事前 create した name が list に含まれる (create は正しい前提)"""
        name = f"e2e-grp-list-{unique_identifier('list')}"
        group_id = _create_group(name)

        result = run_redi("group", "list")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert name in result.stdout
        assert group_id in result.stdout


@pytest.mark.e2e
class TestGroupView:
    """`redi group view <id>` は指定したグループの情報を表示する"""

    def test_succeeds_for_created_group(self):
        """create した group を view すると name が含まれる (create は正しい前提)"""
        name = f"e2e-grp-view-{unique_identifier('view')}"
        group_id = _create_group(name)

        result = run_redi("group", "view", group_id)
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert name in result.stdout


@pytest.mark.e2e
class TestGroupCreate:
    """`redi group create` は新しいグループを作成する"""

    def test_creates_then_view_shows_it(self):
        """create した group が view で取得できる (view は正しい前提)"""
        name = f"e2e-grp-create-{unique_identifier('create')}"
        group_id = _create_group(name)

        view_result = run_redi("group", "view", group_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert name in view_result.stdout


@pytest.mark.e2e
class TestGroupUpdate:
    """`redi group update` は既存のグループを更新する"""

    def test_updates_then_view_shows_new_name(self):
        """create→update した後 view で更新後の name が確認できる (create/view は正しい前提)"""
        original = f"e2e-grp-upd-orig-{unique_identifier('update')}"
        updated = f"e2e-grp-upd-new-{unique_identifier('update')}"
        group_id = _create_group(original)

        update_result = run_redi("group", "update", group_id, "--name", updated)
        assert update_result.returncode == 0, (
            f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
        )

        view_result = run_redi("group", "view", group_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert updated in view_result.stdout
        assert original not in view_result.stdout


@pytest.mark.e2e
class TestGroupDelete:
    """`redi group delete` は指定したグループを削除する"""

    def test_deletes_then_view_fails(self):
        """create→delete した後 view が失敗する (create/view は正しい前提)"""
        name = f"e2e-grp-del-{unique_identifier('delete')}"
        group_id = _create_group(name)

        delete_result = run_redi("group", "delete", group_id, "-y")
        assert delete_result.returncode == 0, (
            f"stdout:\n{delete_result.stdout}\nstderr:\n{delete_result.stderr}"
        )

        view_result = run_redi("group", "view", group_id)
        assert view_result.returncode != 0, (
            f"削除後 view が成功してしまった\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert "Group not found" in view_result.stdout, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
