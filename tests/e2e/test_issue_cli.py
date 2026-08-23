import json
import subprocess

import pytest

from tests.e2e.utils import run_redi, unique_identifier

# バグトラッカーには必須のカスタムフィールドがあり引数だけで作成できないため、
# 削除の検証には機能トラッカーを使う
FEATURE_TRACKER_ID = "2"


def _create_issue(subject: str) -> str:
    """イシューを作成して id を返す。"""
    created = json.loads(
        run_redi(
            "issue",
            "create",
            subject,
            "--project_id",
            "reditest",
            "--tracker_id",
            FEATURE_TRACKER_ID,
            "-d",
            "e2e issue body",
            "--full",
        ).stdout
    )
    return str(created["id"])


@pytest.mark.e2e
class TestIssueView:
    """`redi issue view` はイシューの詳細を表示する"""

    def test_shows_subject_and_description(self):
        """作成したイシューの件名と説明が出る"""
        subject = unique_identifier("e2e-issue-view")
        issue_id = _create_issue(subject)

        viewed = run_redi("issue", "view", issue_id).stdout

        assert subject in viewed
        assert "e2e issue body" in viewed


@pytest.mark.e2e
class TestIssueUpdate:
    """`redi issue update` はイシューを更新する"""

    def test_updated_subject_is_reflected(self):
        """更新した件名が詳細表示に反映される"""
        issue_id = _create_issue(unique_identifier("e2e-issue-update"))
        updated_subject = unique_identifier("e2e-issue-updated")

        run_redi("issue", "update", issue_id, "--subject", updated_subject)

        assert updated_subject in run_redi("issue", "view", issue_id).stdout

    def test_moved_issue_appears_in_destination_project(self):
        """--project_id に identifier を渡すとイシューが移動先プロジェクトの一覧に出る"""
        subject = unique_identifier("e2e-issue-move")
        issue_id = _create_issue(subject)
        destination = unique_identifier("e2e-move-dest")
        run_redi(
            "project",
            "create",
            f"e2e move {destination}",
            destination,
            "--tracker_ids",
            FEATURE_TRACKER_ID,
        )

        run_redi("issue", "update", issue_id, "--project_id", destination)

        assert subject in run_redi("issue", "list", "--project_id", destination).stdout
        assert (
            subject not in run_redi("issue", "list", "--project_id", "reditest").stdout
        )

    def test_exits_with_error_for_missing_destination_project(self):
        """Redmine は存在しない移動先を黙って無視するので、redi 側で弾いて exit 1 にする"""
        issue_id = _create_issue(unique_identifier("e2e-issue-move-missing"))

        with pytest.raises(subprocess.CalledProcessError) as update_error_info:
            run_redi("issue", "update", issue_id, "--project_id", "e2e-no-such-project")

        update_error = update_error_info.value
        assert update_error.returncode == 1
        assert "Project not found: e2e-no-such-project" in update_error.stdout, (
            f"想定外のエラーで update が失敗\n"
            f"stdout:\n{update_error.stdout}\nstderr:\n{update_error.stderr}"
        )


@pytest.mark.e2e
class TestIssueComment:
    """`redi issue comment` はイシューにコメントを追加する"""

    def test_added_comment_is_listed_with_note_url(self):
        """追加したコメントは note 番号つき URL で伝えられ、詳細表示にも出る"""
        issue_id = _create_issue(unique_identifier("e2e-issue-comment"))
        notes = unique_identifier("e2e-comment")

        added = run_redi("issue", "comment", issue_id, notes).stdout

        assert f"/issues/{issue_id}#note-1" in added
        assert notes in run_redi("issue", "view", issue_id).stdout


@pytest.mark.e2e
class TestIssueDelete:
    """`redi issue delete` はイシューを削除する"""

    def test_deleted_issue_disappears_from_list(self):
        """削除したイシューは一覧に出てこなくなる"""
        subject = unique_identifier("e2e-issue-delete")
        issue_id = _create_issue(subject)
        assert subject in run_redi("issue", "list", "--project_id", "reditest").stdout

        run_redi("issue", "delete", issue_id, "--yes")

        assert (
            subject not in run_redi("issue", "list", "--project_id", "reditest").stdout
        )

    def test_exits_with_error_for_missing_issue(self):
        """存在しないイシューの削除は見つからないと伝えて exit 1 で終わる"""
        issue_id = _create_issue(unique_identifier("e2e-issue-missing"))
        run_redi("issue", "delete", issue_id, "--yes")

        with pytest.raises(subprocess.CalledProcessError) as delete_error_info:
            run_redi("issue", "delete", issue_id, "--yes")

        delete_error = delete_error_info.value
        assert delete_error.returncode == 1
        assert f"Issue not found: #{issue_id}" in delete_error.stdout, (
            f"想定外のエラーで delete が失敗\n"
            f"stdout:\n{delete_error.stdout}\nstderr:\n{delete_error.stderr}"
        )
