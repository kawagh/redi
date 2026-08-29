import json
import subprocess

import pytest

from tests.e2e.utils import assert_paginates, run_redi, unique_identifier


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

    def test_slices_list_with_limit_and_offset(self):
        """作成済みの reditest と合わせて3件以上にしてから絞り込む"""
        for _ in range(2):
            name = unique_identifier("e2e-page-project")
            run_redi("project", "create", name, name)

        assert_paginates("project", "list")


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

    def test_creates_with_options(self):
        """--description と --is_public を付けた作成が view に反映される"""
        identifier = unique_identifier("e2e-create-opt")
        name = f"e2e create options {identifier}"

        run_redi(
            "project",
            "create",
            name,
            identifier,
            "--description",
            "e2e description",
            "--is_public",
            "false",
        )

        view_result = run_redi("project", "view", identifier)
        assert "e2e description" in view_result.stdout

    def test_creates_with_additional_fields(self):
        """--homepage / --inherit_members / --enabled_module_names を付けた作成が view に反映される"""
        identifier = unique_identifier("e2e-create-more")
        name = f"e2e create more {identifier}"

        run_redi(
            "project",
            "create",
            name,
            identifier,
            "--homepage",
            "https://example.com/e2e",
            "--inherit_members",
            "true",
            "--enabled_module_names",
            "issue_tracking,wiki",
        )

        full_result = run_redi("project", "view", identifier, "--full")
        assert "https://example.com/e2e" in full_result.stdout
        assert '"inherit_members": true' in full_result.stdout

        modules_result = run_redi(
            "project", "view", identifier, "--include", "enabled_modules"
        )
        assert "issue_tracking" in modules_result.stdout
        assert "wiki" in modules_result.stdout
        assert "news" not in modules_result.stdout

    def test_exits_without_prompting_in_non_interactive(self):
        """引数が足りない場合、非TTYでは対話に入らず exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("project", "create")

        assert e.value.returncode == 1


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

    def test_updates_enabled_modules(self):
        """--enabled_module_names での更新が view の有効モジュールに反映される"""
        identifier = unique_identifier("e2e-update-modules")
        name = f"e2e update modules {identifier}"

        run_redi(
            "project",
            "create",
            name,
            identifier,
            "--enabled_module_names",
            "issue_tracking,wiki",
        )
        run_redi(
            "project",
            "update",
            identifier,
            "--enabled_module_names",
            "issue_tracking",
        )

        view_result = run_redi(
            "project", "view", identifier, "--include", "enabled_modules"
        )
        assert "issue_tracking" in view_result.stdout
        assert "wiki" not in view_result.stdout

    def test_updates_homepage(self):
        """--homepage での更新が view --full に反映される"""
        identifier = unique_identifier("e2e-update-homepage")
        name = f"e2e update homepage {identifier}"

        run_redi("project", "create", name, identifier)
        run_redi(
            "project", "update", identifier, "--homepage", "https://example.com/updated"
        )

        view_result = run_redi("project", "view", identifier, "--full")
        assert "https://example.com/updated" in view_result.stdout

    def test_updates_default_assignee_and_version(self):
        """--default_assigned_to_id / --default_version_id での更新が view に反映される"""
        identifier = unique_identifier("e2e-update-defaults")
        name = f"e2e update defaults {identifier}"
        run_redi("project", "create", name, identifier)
        user_id = json.loads(run_redi("me", "--full").stdout)["id"]
        version_name = unique_identifier("e2e-default-version")
        # 作成の出力は "Created version: <id> <name> <url>" 形式
        version_id = run_redi(
            "version", "create", version_name, "--project_id", identifier
        ).stdout.split()[2]

        run_redi(
            "project",
            "update",
            identifier,
            "--default_assigned_to_id",
            str(user_id),
            "--default_version_id",
            version_id,
        )

        project = json.loads(run_redi("project", "view", identifier, "--full").stdout)
        assert project["default_assignee"]["id"] == user_id
        assert project["default_version"]["id"] == int(version_id)

    def test_empty_value_unsets_default_assignee_and_version(self):
        """空文字の指定は既定の担当者・バージョンの解除になる"""
        identifier = unique_identifier("e2e-unset-defaults")
        name = f"e2e unset defaults {identifier}"
        run_redi("project", "create", name, identifier)
        user_id = json.loads(run_redi("me", "--full").stdout)["id"]
        version_id = run_redi(
            "version",
            "create",
            unique_identifier("e2e-unset-version"),
            "--project_id",
            identifier,
        ).stdout.split()[2]
        run_redi(
            "project",
            "update",
            identifier,
            "--default_assigned_to_id",
            str(user_id),
            "--default_version_id",
            version_id,
        )

        run_redi(
            "project",
            "update",
            identifier,
            "--default_assigned_to_id",
            "",
            "--default_version_id",
            "",
        )

        project = json.loads(run_redi("project", "view", identifier, "--full").stdout)
        assert "default_assignee" not in project
        assert "default_version" not in project


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
        assert "Project not found" in view_error.stderr, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_error.stdout}\nstderr:\n{view_error.stderr}"
        )


@pytest.mark.e2e
class TestProjectArchive:
    """`redi project update --archive` / `--no-archive` はアーカイブを切り替える"""

    def test_archives_then_unarchives(self):
        """archive→unarchive した後 view で取得できる (create/view は正しい前提)"""
        identifier = unique_identifier("e2e-archive")
        name = f"e2e archive {identifier}"

        run_redi("project", "create", name, identifier)
        run_redi("project", "update", identifier, "--archive")
        run_redi("project", "update", identifier, "--no-archive")

        view_result = run_redi("project", "view", identifier)
        assert name in view_result.stdout

    def test_view_of_archived_project_fails_with_reason(self):
        """アーカイブ済みプロジェクトの view は理由を示して失敗する (Redmine は 403 を返す)"""
        identifier = unique_identifier("e2e-archived-view")
        name = f"e2e archived view {identifier}"

        run_redi("project", "create", name, identifier)
        run_redi("project", "update", identifier, "--archive")

        with pytest.raises(subprocess.CalledProcessError) as view_error_info:
            run_redi("project", "view", identifier)
        view_error = view_error_info.value
        assert "Cannot access project" in view_error.stderr, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_error.stdout}\nstderr:\n{view_error.stderr}"
        )
        assert "Traceback" not in view_error.stderr

    def test_fails_for_missing_project(self):
        """存在しないプロジェクトの archive は not found として失敗する"""
        with pytest.raises(subprocess.CalledProcessError) as error_info:
            run_redi("project", "update", "999999", "--archive")

        assert "Project not found" in error_info.value.stderr
