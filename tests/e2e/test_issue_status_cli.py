import pytest

from tests.e2e.utils import run_redi


@pytest.mark.e2e
class TestIssueStatusList:
    """`redi issue_status` はチケットステータス一覧を表示する"""

    def test_lists_default_statuses(self):
        """init-redmine.sh で読み込まれた既定ステータス(新規/進行中/終了)が出力に含まれる"""
        result = run_redi("issue_status")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        for name in ("新規", "進行中", "終了"):
            assert name in result.stdout, (
                f"既定のステータス '{name}' が出力に見当たらない\n{result.stdout}"
            )
