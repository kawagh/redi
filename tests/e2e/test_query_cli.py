import json

import pytest

from tests.e2e.utils import run_redi


@pytest.mark.e2e
class TestQueryList:
    """`redi query` はカスタムクエリ一覧を表示する"""

    def test_lists_default_queries(self):
        """init-redmine.sh で読み込まれた既定のクエリ(担当しているチケット 等)が出力に含まれる"""
        result = run_redi("query")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "担当しているチケット" in result.stdout

    def test_full_outputs_json_array(self):
        """--full は JSON 配列を出力する"""
        result = run_redi("query", "--full")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        parsed = json.loads(result.stdout)
        assert isinstance(parsed, list)
        assert any(q.get("name") == "担当しているチケット" for q in parsed)
