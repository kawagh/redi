import json
import subprocess

import pytest

from tests.e2e.utils import run_redi, unique_identifier

# バグトラッカーには必須のカスタムフィールドがあり引数だけで作成できないため、機能トラッカーを使う
FEATURE_TRACKER_ID = "2"


def _create_issue_with_attachment(tmp_path, body: str = "e2e attachment body") -> str:
    """添付ファイルつきのイシューを作り、添付ファイルの id を返す。"""
    created = json.loads(
        run_redi(
            "issue",
            "create",
            unique_identifier("e2e-attachment"),
            "--project_id",
            "reditest",
            "--tracker_id",
            FEATURE_TRACKER_ID,
            "-d",
            "e2e issue body",
            "--full",
        ).stdout
    )
    issue_id = str(created["id"])
    upload_path = tmp_path / "e2e-attachment.txt"
    upload_path.write_text(body)
    run_redi("issue", "update", issue_id, "--attach", str(upload_path))

    issue = json.loads(run_redi("issue", "view", issue_id, "--full").stdout)
    return str(issue["attachments"][0]["id"])


@pytest.mark.e2e
class TestAttachmentView:
    """`redi attachment view` は添付ファイルの詳細を表示する"""

    def test_shows_uploaded_filename(self, tmp_path):
        """アップロードしたファイル名が出る"""
        attachment_id = _create_issue_with_attachment(tmp_path)

        viewed = run_redi("attachment", "view", attachment_id).stdout

        assert "e2e-attachment.txt" in viewed

    def test_exits_with_error_for_missing_attachment(self):
        """存在しない添付ファイルの表示は見つからないと伝えて exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as error_info:
            run_redi("attachment", "view", "99999999")

        error = error_info.value
        assert error.returncode == 1
        assert "Attachment not found: #99999999" in error.stderr, (
            f"想定外のエラーで view が失敗\n"
            f"stdout:\n{error.stdout}\nstderr:\n{error.stderr}"
        )


@pytest.mark.e2e
class TestAttachmentDownload:
    """`redi attachment download` は添付ファイルの実体を保存する"""

    def test_downloaded_file_has_uploaded_content(self, tmp_path):
        """保存したファイルの中身がアップロードしたものと一致する"""
        body = unique_identifier("e2e-attachment-body")
        attachment_id = _create_issue_with_attachment(tmp_path, body=body)
        output = tmp_path / "downloaded.txt"

        run_redi("attachment", "download", attachment_id, "-o", str(output), "--yes")

        assert output.read_text() == body


@pytest.mark.e2e
class TestAttachmentUpdate:
    """`redi attachment update` は添付ファイルのファイル名・説明を更新する"""

    def test_updated_filename_and_description_are_reflected(self, tmp_path):
        """更新したファイル名と説明が詳細表示に反映される"""
        attachment_id = _create_issue_with_attachment(tmp_path)

        run_redi(
            "attachment",
            "update",
            attachment_id,
            "--filename",
            "renamed.txt",
            "--description",
            "e2e description",
        )

        viewed = run_redi("attachment", "view", attachment_id).stdout
        assert "renamed.txt" in viewed
        assert "e2e description" in viewed


@pytest.mark.e2e
class TestAttachmentDelete:
    """`redi attachment delete` は添付ファイルを削除する"""

    def test_deleted_attachment_is_not_found(self, tmp_path):
        """削除した添付ファイルは見つからなくなる"""
        attachment_id = _create_issue_with_attachment(tmp_path)

        run_redi("attachment", "delete", attachment_id, "--yes")

        with pytest.raises(subprocess.CalledProcessError) as error_info:
            run_redi("attachment", "view", attachment_id)

        error = error_info.value
        assert error.returncode == 1
        assert f"Attachment not found: #{attachment_id}" in error.stderr, (
            f"想定外のエラーで view が失敗\n"
            f"stdout:\n{error.stdout}\nstderr:\n{error.stderr}"
        )
