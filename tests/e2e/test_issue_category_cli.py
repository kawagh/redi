import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_category(name: str) -> str:
    """issue category を作成し category_id を返す。"""
    result = run_redi("issue_category", "create", name)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    # 出力例: "Created category: 1 test-cat-1"
    category_id = result.stdout.strip().split()[2]
    assert category_id.isdigit(), f"想定外の create 出力:\n{result.stdout}"
    return category_id


@pytest.mark.e2e
class TestIssueCategoryList:
    """`redi issue_category list` はカテゴリ一覧を表示する"""

    def test_lists_created_category(self):
        """事前 create した name が list に含まれる (create は正しい前提)"""
        name = f"e2e-cat-list-{unique_identifier('list')}"
        category_id = _create_category(name)

        result = run_redi("issue_category", "list")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert name in result.stdout
        assert category_id in result.stdout


@pytest.mark.e2e
class TestIssueCategoryView:
    """`redi issue_category view <id>` は指定したカテゴリの情報を表示する"""

    def test_succeeds_for_created_category(self):
        """create した category を view すると name が含まれる (create は正しい前提)"""
        name = f"e2e-cat-view-{unique_identifier('view')}"
        category_id = _create_category(name)

        result = run_redi("issue_category", "view", category_id)
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert name in result.stdout


@pytest.mark.e2e
class TestIssueCategoryCreate:
    """`redi issue_category create` は新しいカテゴリを作成する"""

    def test_creates_then_view_shows_it(self):
        """create した category が view で取得できる (view は正しい前提)"""
        name = f"e2e-cat-create-{unique_identifier('create')}"
        category_id = _create_category(name)

        view_result = run_redi("issue_category", "view", category_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert name in view_result.stdout


@pytest.mark.e2e
class TestIssueCategoryUpdate:
    """`redi issue_category update` は既存のカテゴリを更新する"""

    def test_updates_then_view_shows_new_name(self):
        """create→update した後 view で更新後の name が確認できる (create/view は正しい前提)"""
        original = f"e2e-cat-upd-orig-{unique_identifier('update')}"
        updated = f"e2e-cat-upd-new-{unique_identifier('update')}"
        category_id = _create_category(original)

        update_result = run_redi(
            "issue_category", "update", category_id, "--name", updated
        )
        assert update_result.returncode == 0, (
            f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
        )

        view_result = run_redi("issue_category", "view", category_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert updated in view_result.stdout
        assert original not in view_result.stdout


@pytest.mark.e2e
class TestIssueCategoryDelete:
    """`redi issue_category delete` は指定したカテゴリを削除する"""

    def test_deletes_then_view_fails(self):
        """create→delete した後 view が失敗する (create/view は正しい前提)"""
        name = f"e2e-cat-del-{unique_identifier('delete')}"
        category_id = _create_category(name)

        delete_result = run_redi("issue_category", "delete", category_id, "-y")
        assert delete_result.returncode == 0, (
            f"stdout:\n{delete_result.stdout}\nstderr:\n{delete_result.stderr}"
        )

        view_result = run_redi("issue_category", "view", category_id)
        assert view_result.returncode != 0, (
            f"削除後 view が成功してしまった\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert "Category not found" in view_result.stdout, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
