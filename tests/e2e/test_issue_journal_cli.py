import json
import subprocess

import pytest

from tests.e2e.utils import run_redi, unique_identifier

# バグトラッカーには必須のカスタムフィールドがあり引数だけで作成できないため、機能トラッカーを使う
FEATURE_TRACKER_ID = "2"


def _create_issue_with_comment(notes: str) -> tuple[str, str]:
    """コメントを 1 件持つイシューを作成し、(issue_id, journal_id) を返す。"""
    created = json.loads(
        run_redi(
            "issue",
            "create",
            unique_identifier("e2e-issue-journal"),
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
    run_redi("issue", "comment", issue_id, notes)
    viewed = json.loads(run_redi("issue", "view", issue_id, "--full").stdout)
    journal_id = str(
        next(j["id"] for j in viewed["journals"] if j.get("notes") == notes)
    )
    return issue_id, journal_id


@pytest.mark.e2e
class TestIssueJournalUpdate:
    """`redi issue_journal update` はコメントを更新する"""

    def test_updated_notes_are_reflected(self):
        """更新後の本文がイシューの詳細表示に出て、更新前の本文は出なくなる"""
        notes = unique_identifier("e2e-journal-before")
        updated_notes = unique_identifier("e2e-journal-after")
        issue_id, journal_id = _create_issue_with_comment(notes)

        run_redi("issue_journal", "update", journal_id, updated_notes)

        viewed = run_redi("issue", "view", issue_id).stdout
        assert updated_notes in viewed
        assert notes not in viewed

    def test_exits_with_error_for_missing_journal(self):
        """存在しないコメントの更新は見つからないと伝えて exit 1 で終わる"""
        with pytest.raises(subprocess.CalledProcessError) as update_error_info:
            run_redi("issue_journal", "update", "99999999", "notes")

        update_error = update_error_info.value
        assert update_error.returncode == 1
        assert "Issue journal not found: #99999999" in update_error.stderr, (
            f"想定外のエラーで update が失敗\n"
            f"stdout:\n{update_error.stdout}\nstderr:\n{update_error.stderr}"
        )


@pytest.mark.e2e
class TestIssueJournalDelete:
    """`redi issue_journal delete` はコメントを削除する"""

    def test_deleted_notes_disappear_from_issue(self):
        """削除したコメントの本文はイシューの詳細表示に出てこなくなる"""
        notes = unique_identifier("e2e-journal-delete")
        issue_id, journal_id = _create_issue_with_comment(notes)
        assert notes in run_redi("issue", "view", issue_id).stdout

        run_redi("issue_journal", "delete", journal_id, "--yes")

        assert notes not in run_redi("issue", "view", issue_id).stdout
