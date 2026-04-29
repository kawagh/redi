import pytest

from tests.e2e.utils import run_redi


@pytest.mark.e2e
class TestIssuePriorityList:
    """`redi issue_priority` はチケット優先度一覧を表示する"""

    def test_lists_default_priorities(self):
        """init-redmine.sh で読み込まれた既定優先度(低め/通常/高め/今すぐ)が出力に含まれる"""
        result = run_redi("issue_priority")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        for name in ("低め", "通常", "高め", "今すぐ"):
            assert name in result.stdout, (
                f"既定の優先度 '{name}' が出力に見当たらない\n{result.stdout}"
            )
