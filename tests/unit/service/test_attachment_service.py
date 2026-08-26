from types import SimpleNamespace

import pytest

from redi import config
from redi.api.attachment import AttachmentNotFoundException
from redi.service import attachment_service


@pytest.fixture(autouse=True)
def redmine_url(monkeypatch):
    monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")


@pytest.fixture
def attachment():
    return {
        "id": 7,
        "filename": "report.txt",
        "content_url": "http://localhost:3001/attachments/download/7/report.txt",
    }


class TestUploadFile:
    """upload_file がアップロード前に確認すること"""

    @pytest.fixture
    def stub_upload(self, monkeypatch):
        """アップロード API を差し替え、呼ばれたパスを記録する。"""
        called: list[str] = []
        monkeypatch.setattr(
            attachment_service.attachment_api,
            "upload_file",
            lambda file_path: called.append(file_path) or {"token": "t"},
        )
        return called

    def test_missing_file_raises_without_upload(self, stub_upload, tmp_path):
        """存在しないパスならアップロードせず例外にする"""
        missing = tmp_path / "missing.txt"

        with pytest.raises(attachment_service.LocalFileNotFoundException) as e:
            attachment_service.upload_file(str(missing))

        assert e.value.path == str(missing)
        assert stub_upload == []

    def test_directory_raises_without_upload(self, stub_upload, tmp_path):
        """ディレクトリを指定した場合もアップロードせず例外にする"""
        with pytest.raises(attachment_service.LocalFileNotFoundException):
            attachment_service.upload_file(str(tmp_path))

        assert stub_upload == []


class TestResolveDownloadPath:
    """resolve_download_path が決める保存先"""

    def test_without_output_uses_filename(self, attachment):
        """出力先を指定しなければカレントディレクトリに添付ファイル名で保存する"""
        assert str(attachment_service.resolve_download_path(attachment, None)) == (
            "report.txt"
        )

    def test_directory_output_joins_filename(self, attachment, tmp_path):
        """ディレクトリを指定するとその配下に添付ファイル名で保存する"""
        path = attachment_service.resolve_download_path(attachment, str(tmp_path))

        assert path == tmp_path / "report.txt"

    def test_file_output_is_used_as_is(self, attachment, tmp_path):
        """ファイルパスを指定するとそのパスに保存する"""
        output = tmp_path / "renamed.txt"

        path = attachment_service.resolve_download_path(attachment, str(output))

        assert path == output

    def test_filename_with_directory_is_stripped(self, attachment):
        """Redmine 側のファイル名にディレクトリが含まれても保存先を外に出さない"""
        attachment["filename"] = "../../etc/passwd"

        assert str(attachment_service.resolve_download_path(attachment, None)) == (
            "passwd"
        )


class TestResolveDownloadUrlPath:
    """resolve_download_url_path が返すパス"""

    def test_returns_path_under_redmine_url(self, attachment):
        """Redmine のホスト配下ならホストを除いたパスを返す"""
        assert (
            attachment_service.resolve_download_url_path(attachment)
            == "/attachments/download/7/report.txt"
        )

    def test_other_host_raises(self, attachment):
        """別ホストの content_url は API キーを送らないよう例外にする"""
        attachment["content_url"] = "http://evil.example.com/attachments/download/7"

        with pytest.raises(attachment_service.UnexpectedContentUrlException) as e:
            attachment_service.resolve_download_url_path(attachment)

        assert e.value.url == "http://evil.example.com/attachments/download/7"


class TestDownloadAttachment:
    """download_attachment の書き込み手順"""

    @pytest.fixture
    def stub_content(self, monkeypatch):
        """実体取得を差し替える。`chunks` が None なら 404 相当。"""
        state = SimpleNamespace(chunks=[b"ab", b"cd"], url_paths=[])

        def fake_iter_attachment_content(url_path):
            state.url_paths.append(url_path)
            return state.chunks

        monkeypatch.setattr(
            attachment_service.attachment_api,
            "iter_attachment_content",
            fake_iter_attachment_content,
        )
        return state

    def test_writes_chunks_to_path(self, attachment, stub_content, tmp_path):
        """取得したチャンクを保存先に連結して書き込む"""
        path = tmp_path / "report.txt"

        attachment_service.download_attachment(attachment, path)

        assert path.read_bytes() == b"abcd"
        assert stub_content.url_paths == ["/attachments/download/7/report.txt"]

    def test_missing_content_raises(self, attachment, stub_content, tmp_path):
        """実体が無ければ保存先を作らず例外にする"""
        stub_content.chunks = None
        path = tmp_path / "report.txt"

        with pytest.raises(AttachmentNotFoundException) as e:
            attachment_service.download_attachment(attachment, path)

        assert e.value.attachment_id == "7"
        assert not path.exists()


class TestAttachmentUrl:
    """attachment_url が組み立てる URL"""

    def test_url(self):
        """添付ファイル ID から Web UI の URL を組み立てる"""
        assert (
            attachment_service.attachment_url("7")
            == "http://localhost:3001/attachments/7"
        )
