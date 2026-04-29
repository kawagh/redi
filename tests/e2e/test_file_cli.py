from pathlib import Path

import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_project_for_file_test() -> str:
    """file モジュールが有効なプロジェクトを作成し identifier を返す。

    init-redmine.sh で作成される reditest プロジェクトは files モジュールが
    無効なため、新規プロジェクトを使う必要がある(403 になる)。
    """
    identifier = unique_identifier("e2e-file")
    name = f"e2e file {identifier}"
    result = run_redi("project", "create", name, identifier)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return identifier


def _upload_file(project_identifier: str, file_path: Path) -> None:
    result = run_redi("file", "create", str(file_path), "-p", project_identifier)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


@pytest.mark.e2e
class TestFileList:
    """`redi file list` はプロジェクトのファイル一覧を表示する"""

    def test_lists_uploaded_file(self, tmp_path):
        """事前 upload したファイル名が list に含まれる (create は正しい前提)"""
        project_identifier = _create_project_for_file_test()
        filename = f"{unique_identifier('listfile')}.txt"
        file_path = tmp_path / filename
        file_path.write_text("file list e2e content")
        _upload_file(project_identifier, file_path)

        result = run_redi("file", "-p", project_identifier, "list")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert filename in result.stdout


@pytest.mark.e2e
class TestFileCreate:
    """`redi file create` はファイルをプロジェクトにアップロードする"""

    def test_creates_then_list_shows_it(self, tmp_path):
        """upload したファイルが list で取得できる (list は正しい前提)"""
        project_identifier = _create_project_for_file_test()
        filename = f"{unique_identifier('createfile')}.txt"
        file_path = tmp_path / filename
        file_path.write_text("file create e2e content")

        upload_result = run_redi(
            "file", "create", str(file_path), "-p", project_identifier
        )
        assert upload_result.returncode == 0, (
            f"stdout:\n{upload_result.stdout}\nstderr:\n{upload_result.stderr}"
        )

        list_result = run_redi("file", "-p", project_identifier, "list")
        assert list_result.returncode == 0, (
            f"stdout:\n{list_result.stdout}\nstderr:\n{list_result.stderr}"
        )
        assert filename in list_result.stdout
