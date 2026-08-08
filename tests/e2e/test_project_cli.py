import subprocess

import pytest

from tests.e2e.utils import run_redi, unique_identifier


@pytest.mark.e2e
class TestProjectList:
    """`redi project list` はプロジェクト一覧を表示する"""

    def test_lists_created_project(self):
        """事前に create した identifier が list に含まれる (create は正しい前提)"""
        identifier = unique_identifier("e2e-list")
        name = f"e2e list {identifier}"

        run_redi("project", "create", name, identifier)

        result = run_redi("project", "list")
        assert identifier in result.stdout


@pytest.mark.e2e
class TestProjectView:
    """`redi project view <id>` は指定したプロジェクトの情報を表示する"""

    def test_succeeds_for_existing_project_id(self):
        """init-redmine.sh で作成された id=1 のプロジェクト(reditest)を表示すると exit 0 で成功する"""
        result = run_redi("project", "view", "1")
        assert "reditest" in result.stdout


@pytest.mark.e2e
class TestProjectCreate:
    """`redi project create` は新しいプロジェクトを作成する"""

    def test_creates_then_view_shows_it(self):
        """create したプロジェクトが view で取得できる (view は正しい前提)"""
        identifier = unique_identifier("e2e-create")
        name = f"e2e create {identifier}"

        run_redi("project", "create", name, identifier)

        view_result = run_redi("project", "view", identifier)
        assert name in view_result.stdout
        assert identifier in view_result.stdout


@pytest.mark.e2e
class TestProjectUpdate:
    """`redi project update` は既存のプロジェクトを更新する"""

    def test_updates_then_view_shows_new_name(self):
        """create→update した後 view で更新後の name が確認できる (create/view は正しい前提)"""
        identifier = unique_identifier("e2e-update")
        original_name = f"e2e update original {identifier}"
        updated_name = f"e2e update updated {identifier}"

        run_redi("project", "create", original_name, identifier)
        run_redi("project", "update", identifier, "--name", updated_name)

        view_result = run_redi("project", "view", identifier)
        assert updated_name in view_result.stdout
        assert original_name not in view_result.stdout


@pytest.mark.e2e
class TestProjectDelete:
    """`redi project delete` は指定したプロジェクトを削除する"""

    def test_deletes_then_view_fails(self):
        """create→delete した後 view が失敗する (create/view は正しい前提)"""
        identifier = unique_identifier("e2e-delete")
        name = f"e2e delete {identifier}"

        run_redi("project", "create", name, identifier)
        run_redi("project", "delete", identifier, "-y")

        with pytest.raises(subprocess.CalledProcessError) as view_error_info:
            run_redi("project", "view", identifier)
        view_error = view_error_info.value
        assert "Project not found" in view_error.stdout, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_error.stdout}\nstderr:\n{view_error.stderr}"
        )
