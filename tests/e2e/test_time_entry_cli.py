import json
import subprocess

import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _first_activity_id() -> str:
    """作業分類の id を1つ返す。分類の並びは Redmine の初期データ次第なので先頭を使う。"""
    first_line = run_redi("time_entry_activity", "list").stdout.splitlines()[0]
    return first_line.split()[0]


def _create_time_entry(comments: str) -> str:
    """プロジェクトに紐づく作業時間を作成して id を返す。

    作成コマンドは id を JSON で返さないため、一意な comments で一覧から引き当てる。
    """
    run_redi(
        "time_entry",
        "create",
        "1.0",
        "--project_id",
        "reditest",
        "--activity_id",
        _first_activity_id(),
        "--comments",
        comments,
    )
    entries = json.loads(
        run_redi("time_entry", "list", "--project_id", "reditest", "--full").stdout
    )
    return str(next(te["id"] for te in entries if te.get("comments") == comments))


@pytest.mark.e2e
class TestTimeEntryDelete:
    """`redi time_entry delete` は作業時間を削除する"""

    def test_deleted_time_entry_disappears_from_list(self):
        """削除した作業時間は一覧に出てこなくなる"""
        comments = unique_identifier("e2e-te-delete")
        time_entry_id = _create_time_entry(comments)
        assert (
            comments
            in run_redi("time_entry", "list", "--project_id", "reditest").stdout
        )

        run_redi("time_entry", "delete", time_entry_id, "--yes")

        assert (
            comments
            not in run_redi("time_entry", "list", "--project_id", "reditest").stdout
        )

    def test_exits_with_error_for_missing_time_entry(self):
        """存在しない作業時間の削除は見つからないと伝えて exit 1 で終わる"""
        time_entry_id = _create_time_entry(unique_identifier("e2e-te-missing"))
        run_redi("time_entry", "delete", time_entry_id, "--yes")

        with pytest.raises(subprocess.CalledProcessError) as delete_error_info:
            run_redi("time_entry", "delete", time_entry_id, "--yes")

        delete_error = delete_error_info.value
        assert delete_error.returncode == 1
        assert f"Time entry not found: {time_entry_id}" in delete_error.stdout, (
            f"想定外のエラーで delete が失敗\n"
            f"stdout:\n{delete_error.stdout}\nstderr:\n{delete_error.stderr}"
        )
