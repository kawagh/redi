import json

import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_file(tmp_path, prefix: str) -> str:
    """`<prefix>-<uuid8>.txt` を作り、reditest プロジェクトに登録してファイル名を返す。"""
    filename = f"{unique_identifier(prefix)}.txt"
    file_path = tmp_path / filename
    file_path.write_text("redi e2e file\n", encoding="utf-8")
    run_redi("file", "create", str(file_path))
    return filename


@pytest.mark.e2e
class TestFileCreate:
    """`redi file create <path>` はプロジェクトにファイルを登録する"""

    def test_creates_then_list_shows_it(self, tmp_path):
        """create したファイルが list に含まれる (list は正しい前提)"""
        filename = _create_file(tmp_path, "e2e-file-create")

        result = run_redi("file", "list")
        assert filename in result.stdout

    def test_creates_with_description(self, tmp_path):
        """--description で渡した説明が登録される"""
        description = unique_identifier("e2e-file-description")
        filename = f"{unique_identifier('e2e-file-desc')}.txt"
        file_path = tmp_path / filename
        file_path.write_text("redi e2e file\n", encoding="utf-8")

        run_redi("file", "create", str(file_path), "--description", description)

        files = json.loads(run_redi("file", "list", "--full").stdout)
        created = next(f for f in files if f["filename"] == filename)
        assert created["description"] == description


@pytest.mark.e2e
class TestFileList:
    """`redi file list` はプロジェクトのファイル一覧を表示する"""

    def test_lists_id_and_filename(self, tmp_path):
        """id とファイル名を 1 行に表示する (create は正しい前提)"""
        filename = _create_file(tmp_path, "e2e-file-list")

        files = json.loads(run_redi("file", "list", "--full").stdout)
        created = next(f for f in files if f["filename"] == filename)

        result = run_redi("file", "list")
        assert f"{created['id']} {filename}" in result.stdout
