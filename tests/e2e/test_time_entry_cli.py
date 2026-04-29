import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_time_entry(hours: str = "1.5", comments: str | None = None) -> str:
    """time entry を作成し time_entry_id を返す。

    project_id=1 は init-redmine.sh で作成される reditest プロジェクト。
    redi の time_entry API は identifier を内部で解決する際にプロジェクト一覧の
    既定 limit(25) でしか引かないので、ここでは数値 id を直接指定する。
    activity_id 9 = 開発作業 (init-redmine.sh で読み込まれた既定値)。
    """
    args = [
        "time_entry",
        "create",
        hours,
        "-p",
        "1",
        "--activity_id",
        "9",
    ]
    if comments is not None:
        args += ["--comments", comments]
    result = run_redi(*args)
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    # 出力例: "Logged time entry: 1 1.5h (2026-04-29)"
    time_entry_id = result.stdout.strip().split()[3]
    assert time_entry_id.isdigit(), f"想定外の create 出力:\n{result.stdout}"
    return time_entry_id


@pytest.mark.e2e
class TestTimeEntryList:
    """`redi time_entry list` は作業時間記録一覧を表示する"""

    def test_lists_created_time_entry(self):
        """事前 create した time entry の id が list に含まれる (create は正しい前提)"""
        comment = f"te list {unique_identifier('list')}"
        time_entry_id = _create_time_entry(comments=comment)

        result = run_redi("time_entry", "list")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert comment in result.stdout
        assert any(
            line.startswith(f"{time_entry_id} ") for line in result.stdout.splitlines()
        ), f"time_entry_id={time_entry_id} が list に見当たらない\n{result.stdout}"


@pytest.mark.e2e
class TestTimeEntryView:
    """`redi time_entry view <id>` は指定した作業時間記録の情報を表示する"""

    def test_succeeds_for_created_time_entry(self):
        """create した time entry を view すると comments が含まれる (create は正しい前提)"""
        comment = f"te view {unique_identifier('view')}"
        time_entry_id = _create_time_entry(comments=comment)

        result = run_redi("time_entry", "view", time_entry_id)
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert comment in result.stdout


@pytest.mark.e2e
class TestTimeEntryCreate:
    """`redi time_entry create` は新しい作業時間記録を作成する"""

    def test_creates_then_view_shows_it(self):
        """create した time entry が view で取得できる (view は正しい前提)"""
        comment = f"te create {unique_identifier('create')}"
        time_entry_id = _create_time_entry(comments=comment)

        view_result = run_redi("time_entry", "view", time_entry_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert comment in view_result.stdout


@pytest.mark.e2e
class TestTimeEntryUpdate:
    """`redi time_entry update` は既存の作業時間記録を更新する"""

    def test_updates_then_view_shows_new_comments(self):
        """create→update した後 view で更新後の comments が確認できる (create/view は正しい前提)"""
        original = f"te orig {unique_identifier('update')}"
        updated = f"te new {unique_identifier('update')}"
        time_entry_id = _create_time_entry(comments=original)

        update_result = run_redi(
            "time_entry", "update", time_entry_id, "--comments", updated
        )
        assert update_result.returncode == 0, (
            f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
        )

        view_result = run_redi("time_entry", "view", time_entry_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert updated in view_result.stdout
        assert original not in view_result.stdout


@pytest.mark.e2e
class TestTimeEntryDelete:
    """`redi time_entry delete` は指定した作業時間記録を削除する"""

    def test_deletes_then_view_fails(self):
        """create→delete した後 view が失敗する (create/view は正しい前提)"""
        comment = f"te del {unique_identifier('delete')}"
        time_entry_id = _create_time_entry(comments=comment)

        delete_result = run_redi("time_entry", "delete", time_entry_id, "-y")
        assert delete_result.returncode == 0, (
            f"stdout:\n{delete_result.stdout}\nstderr:\n{delete_result.stderr}"
        )

        view_result = run_redi("time_entry", "view", time_entry_id)
        assert view_result.returncode != 0, (
            f"削除後 view が成功してしまった\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert "Time entry not found" in view_result.stdout, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
