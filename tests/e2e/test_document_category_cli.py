import pytest

from tests.e2e.utils import run_redi


@pytest.mark.e2e
class TestDocumentCategoryList:
    """`redi document_category` は文書カテゴリ一覧を表示する"""

    def test_lists_default_categories(self):
        """init-redmine.sh で読み込まれた既定の文書カテゴリ(ユーザー文書/技術文書)が出力に含まれる"""
        result = run_redi("document_category")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        for name in ("ユーザー文書", "技術文書"):
            assert name in result.stdout, (
                f"既定の文書カテゴリ '{name}' が出力に見当たらない\n{result.stdout}"
            )
