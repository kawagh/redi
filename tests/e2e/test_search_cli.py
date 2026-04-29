import pytest

from tests.e2e.utils import run_redi, unique_identifier


@pytest.mark.e2e
class TestSearch:
    """`redi search <query>` は Redmine の全文検索結果を表示する"""

    def test_finds_created_issue_subject(self):
        """事前 create した issue の subject が search の結果に含まれる (create/view は正しい前提)"""
        token = unique_identifier("search-token")
        subject = f"e2e search target {token}"

        # bug トラッカー(id=1) は必須カスタムフィールドが設定されているので id=2 (機能) を使う
        create_result = run_redi(
            "issue", "create", subject, "--tracker_id", "2", "--description", "search test"
        )
        assert create_result.returncode == 0, (
            f"stdout:\n{create_result.stdout}\nstderr:\n{create_result.stderr}"
        )

        result = run_redi("search", token)
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert token in result.stdout, (
            f"作成した token が search 結果に見当たらない\n{result.stdout}"
        )
