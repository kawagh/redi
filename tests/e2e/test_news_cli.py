import json

import pytest

from tests.e2e.utils import run_redi


@pytest.mark.e2e
class TestNewsList:
    """`redi news` はニュース一覧を表示する"""

    def test_runs_successfully(self):
        """REST API 経由での news 作成手段が無いため、コマンドが成功し --full 出力が JSON 配列であることのみ検証する"""
        result = run_redi("news")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )

        full_result = run_redi("news", "--full")
        assert full_result.returncode == 0, (
            f"stdout:\n{full_result.stdout}\nstderr:\n{full_result.stderr}"
        )
        parsed = json.loads(full_result.stdout)
        assert isinstance(parsed, list)
