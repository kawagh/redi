import pytest

from tests.e2e.utils import run_redi


@pytest.mark.e2e
class TestCustomFieldList:
    """`redi custom_field` はカスタムフィールド一覧を表示する"""

    def test_lists_init_custom_field(self):
        """init-redmine.sh で作成された 'バージョン' カスタムフィールドが出力に含まれる"""
        result = run_redi("custom_field")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "バージョン" in result.stdout
