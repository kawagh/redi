import pytest

from tests.e2e.utils import run_redi


@pytest.mark.e2e
class TestTimeEntryActivityList:
    """`redi time_entry_activity` は作業分類一覧を表示する"""

    def test_lists_default_activities(self):
        """init-redmine.sh で読み込まれた既定の作業分類(設計作業/開発作業)が出力に含まれる"""
        result = run_redi("time_entry_activity")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        for name in ("設計作業", "開発作業"):
            assert name in result.stdout, (
                f"既定の作業分類 '{name}' が出力に見当たらない\n{result.stdout}"
            )
