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
