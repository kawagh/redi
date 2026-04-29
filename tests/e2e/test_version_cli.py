import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_version(name: str) -> str:
    """version を作成し version_id を返す。"""
    result = run_redi("version", "create", name)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    # 出力例: "Created version: 1 v-test-1 http://localhost:3000/versions/1"
    parts = result.stdout.strip().split()
    version_id = parts[2]
    assert version_id.isdigit(), f"想定外の create 出力:\n{result.stdout}"
    return version_id


@pytest.mark.e2e
class TestVersionList:
    """`redi version list` はバージョン一覧を表示する"""

    def test_lists_created_version(self):
        """事前 create した name が list に含まれる (create は正しい前提)"""
        name = f"e2e-version-list-{unique_identifier('list')}"
        version_id = _create_version(name)

        result = run_redi("version", "list")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert name in result.stdout
        assert version_id in result.stdout


@pytest.mark.e2e
class TestVersionView:
    """`redi version view <id>` は指定したバージョンの情報を表示する"""

    def test_succeeds_for_created_version(self):
        """create した version を view すると name が含まれる (create は正しい前提)"""
        name = f"e2e-version-view-{unique_identifier('view')}"
        version_id = _create_version(name)

        result = run_redi("version", "view", version_id)
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert name in result.stdout


@pytest.mark.e2e
class TestVersionCreate:
    """`redi version create` は新しいバージョンを作成する"""

    def test_creates_then_view_shows_it(self):
        """create した version が view で取得できる (view は正しい前提)"""
        name = f"e2e-version-create-{unique_identifier('create')}"
        version_id = _create_version(name)

        view_result = run_redi("version", "view", version_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert name in view_result.stdout


@pytest.mark.e2e
class TestVersionUpdate:
    """`redi version update` は既存のバージョンを更新する"""

    def test_updates_then_view_shows_new_name(self):
        """create→update した後 view で更新後の name が確認できる (create/view は正しい前提)"""
        original = f"e2e-version-update-orig-{unique_identifier('update')}"
        updated = f"e2e-version-update-new-{unique_identifier('update')}"
        version_id = _create_version(original)

        update_result = run_redi("version", "update", version_id, "--name", updated)
        assert update_result.returncode == 0, (
            f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
        )

        view_result = run_redi("version", "view", version_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert updated in view_result.stdout
        assert original not in view_result.stdout


@pytest.mark.e2e
class TestVersionDelete:
    """`redi version delete` は指定したバージョンを削除する"""

    def test_deletes_then_view_fails(self):
        """create→delete した後 view が失敗する (create/view は正しい前提)"""
        name = f"e2e-version-delete-{unique_identifier('delete')}"
        version_id = _create_version(name)

        delete_result = run_redi("version", "delete", version_id, "-y")
        assert delete_result.returncode == 0, (
            f"stdout:\n{delete_result.stdout}\nstderr:\n{delete_result.stderr}"
        )

        view_result = run_redi("version", "view", version_id)
        assert view_result.returncode != 0, (
            f"削除後 view が成功してしまった\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert "Version not found" in view_result.stdout, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
