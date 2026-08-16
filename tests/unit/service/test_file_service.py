import pytest

from redi.service import file_service


@pytest.fixture
def stub_file_api(monkeypatch):
    """アップロードと project files への登録を記録し、HTTP を呼ばないようにする。

    リクエストが Redmine に正しく届くかは E2E (`tests/e2e/test_file_cli.py`) で見る。
    """

    calls: list[tuple] = []

    def fake_upload_file(file_path):
        calls.append(("upload", file_path))
        return {
            "token": "token-1",
            "filename": "report.txt",
            "content_type": "text/plain",
        }

    def fake_create_file(project_id, upload, version_id=None, description=None):
        calls.append(("create", project_id, upload, version_id, description))

    monkeypatch.setattr(file_service, "upload_file", fake_upload_file)
    monkeypatch.setattr(file_service.file_api, "create_file", fake_create_file)
    return calls


class TestCreateFile:
    """create_file のアップロードと登録の手順"""

    def test_uploads_then_registers_with_token(self, stub_file_api):
        """アップロードで得た token を project files の登録に渡す"""
        file_service.create_file("demo", "/tmp/report.txt")

        assert stub_file_api == [
            ("upload", "/tmp/report.txt"),
            (
                "create",
                "demo",
                {
                    "token": "token-1",
                    "filename": "report.txt",
                    "content_type": "text/plain",
                },
                None,
                None,
            ),
        ]

    def test_passes_version_and_description(self, stub_file_api):
        """version_id と description は登録時にそのまま渡す"""
        file_service.create_file(
            "demo", "/tmp/report.txt", version_id=3, description="説明"
        )

        _, create = stub_file_api
        assert create[3] == 3
        assert create[4] == "説明"

    def test_returns_uploaded_filename(self, stub_file_api):
        """登録したファイル名を返す"""
        assert file_service.create_file("demo", "/tmp/report.txt") == "report.txt"
