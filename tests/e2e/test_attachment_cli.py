import json
from pathlib import Path

import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_issue_with_attachment(tmp_path: Path, content: str) -> tuple[str, str]:
    """ファイルを添付した issue を作成し (issue_id, attachment_id) を返す。"""
    subject = f"e2e attachment {unique_identifier('att')}"
    create_result = run_redi(
        "issue", "create", subject, "--tracker_id", "2", "--description", "att test"
    )
    assert create_result.returncode == 0, (
        f"stdout:\n{create_result.stdout}\nstderr:\n{create_result.stderr}"
    )
    issue_id = create_result.stdout.strip().rsplit("/", 1)[-1]
    assert issue_id.isdigit(), f"想定外の create 出力:\n{create_result.stdout}"

    file_path = tmp_path / f"{unique_identifier('attfile')}.txt"
    file_path.write_text(content)

    update_result = run_redi(
        "issue", "update", issue_id, "--attach", str(file_path), "--notes", "attaching"
    )
    assert update_result.returncode == 0, (
        f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
    )

    view_result = run_redi(
        "issue", "view", issue_id, "--include", "attachments", "--full"
    )
    assert view_result.returncode == 0, (
        f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
    )
    parsed = json.loads(view_result.stdout)
    attachments = parsed.get("attachments") or []
    assert attachments, f"attachment が紐付いていない:\n{view_result.stdout}"
    return issue_id, str(attachments[0]["id"])


@pytest.mark.e2e
class TestAttachmentView:
    """`redi attachment view <id>` は指定した添付の情報を表示する"""

    def test_succeeds_for_existing_attachment(self, tmp_path):
        """issue に添付したファイルの id を view すると filename が含まれる"""
        _, attachment_id = _create_issue_with_attachment(tmp_path, "view test content")

        result = run_redi("attachment", "view", attachment_id)
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert ".txt" in result.stdout


@pytest.mark.e2e
class TestAttachmentUpdate:
    """`redi attachment update` は添付ファイルの description を更新する"""

    def test_updates_then_view_shows_new_description(self, tmp_path):
        """update 後に view すると更新後の description が含まれる"""
        _, attachment_id = _create_issue_with_attachment(tmp_path, "update test content")
        new_description = f"e2e desc {unique_identifier('attdesc')}"

        update_result = run_redi(
            "attachment", "update", attachment_id, "-d", new_description
        )
        assert update_result.returncode == 0, (
            f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
        )

        view_result = run_redi("attachment", "view", attachment_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert new_description in view_result.stdout


@pytest.mark.e2e
class TestAttachmentDelete:
    """`redi attachment delete` は指定した添付ファイルを削除する"""

    def test_deletes_then_view_fails(self, tmp_path):
        """delete 後に view が失敗する"""
        _, attachment_id = _create_issue_with_attachment(tmp_path, "delete test content")

        delete_result = run_redi("attachment", "delete", attachment_id, "-y")
        assert delete_result.returncode == 0, (
            f"stdout:\n{delete_result.stdout}\nstderr:\n{delete_result.stderr}"
        )

        view_result = run_redi("attachment", "view", attachment_id)
        assert view_result.returncode != 0, (
            f"削除後 view が成功してしまった\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert "Attachment not found" in view_result.stdout, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
