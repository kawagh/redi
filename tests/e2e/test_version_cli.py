import json
import subprocess

import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_version(name: str, *args: str) -> str:
    """バージョンを作成して id を返す。"""
    created = run_redi("version", "create", name, "--project_id", "reditest", *args)
    # 作成の出力は "Created version: <id> <name> <url>" 形式
    return created.stdout.split()[2]


@pytest.mark.e2e
class TestVersionView:
    """`redi version view` はバージョンの詳細を表示する"""

    def test_shows_created_fields(self):
        """作成時に指定した名前・期日・説明が出る"""
        name = unique_identifier("e2e-version-view")
        version_id = _create_version(
            name, "--due_date", "2030-12-31", "-d", "e2e version body"
        )

        viewed = run_redi("version", "view", version_id).stdout

        assert name in viewed
        assert "2030-12-31" in viewed
        assert "e2e version body" in viewed

    def test_full_returns_json(self):
        """--full では取得した JSON を返す"""
        name = unique_identifier("e2e-version-full")
        version_id = _create_version(name)

        version = json.loads(run_redi("version", "view", version_id, "--full").stdout)

        assert version["id"] == int(version_id)
        assert version["name"] == name
        assert version["project"]["name"] == "reditestプロジェクト"

    def test_exits_with_error_for_missing_version(self):
        """存在しないバージョンの表示は exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("version", "view", "99999")

        assert e.value.returncode == 1


@pytest.mark.e2e
class TestVersionUpdate:
    """`redi version update` はバージョンを更新する"""

    def test_updated_fields_are_reflected(self):
        """更新した名前・状態が詳細表示に反映される"""
        version_id = _create_version(unique_identifier("e2e-version-update"))
        updated_name = unique_identifier("e2e-version-updated")

        run_redi(
            "version", "update", version_id, "-n", updated_name, "--status", "locked"
        )

        viewed = run_redi("version", "view", version_id).stdout
        assert updated_name in viewed
        assert "locked" in viewed

    def test_empty_description_clears_value(self):
        """--description "" は説明を消す"""
        version_id = _create_version(
            unique_identifier("e2e-version-clear"), "-d", "e2e version body"
        )

        run_redi("version", "update", version_id, "-d", "")

        version = json.loads(run_redi("version", "view", version_id, "--full").stdout)
        assert version["description"] == ""

    def test_exits_with_error_for_missing_version(self):
        """存在しないバージョンの更新は exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("version", "update", "99999", "-n", "e2e-version-missing")

        assert e.value.returncode == 1

    def test_exits_with_error_for_invalid_value(self):
        """Redmine が受け付けない値での更新は exit 1 で終わる"""
        version_id = _create_version(unique_identifier("e2e-version-invalid"))

        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("version", "update", version_id, "--due_date", "not-a-date")

        assert e.value.returncode == 1


@pytest.mark.e2e
class TestVersionDelete:
    """`redi version delete` はバージョンを削除する"""

    def test_deleted_version_disappears_from_list(self):
        """削除したバージョンは一覧に出てこなくなる"""
        name = unique_identifier("e2e-version-delete")
        version_id = _create_version(name)
        assert name in run_redi("version", "list", "-p", "reditest").stdout

        run_redi("version", "delete", version_id, "--yes")

        assert name not in run_redi("version", "list", "-p", "reditest").stdout

    def test_exits_with_error_for_missing_version(self):
        """存在しないバージョンの削除は exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("version", "delete", "99999", "--yes")

        assert e.value.returncode == 1
