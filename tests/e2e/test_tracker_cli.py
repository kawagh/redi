import pytest

from tests.e2e.utils import run_redi


@pytest.mark.e2e
class TestTrackerList:
    """`redi tracker` はトラッカー一覧を表示する"""

    def test_lists_default_trackers(self):
        """init-redmine.sh で読み込まれた既定トラッカー(バグ/機能/サポート)が出力に含まれる"""
        result = run_redi("tracker")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        for name in ("バグ", "機能", "サポート"):
            assert name in result.stdout, (
                f"既定のトラッカー '{name}' が出力に見当たらない\n{result.stdout}"
            )
