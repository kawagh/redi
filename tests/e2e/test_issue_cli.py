import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_issue(subject: str) -> str:
    """非インタラクティブに issue を作成し issue_id を返す。

    bug トラッカー(id=1) は init-redmine.sh で必須カスタムフィールドが
    設定されているので、それ以外のトラッカー(id=2 機能)を使う。
    """
    result = run_redi(
        "issue", "create", subject, "--tracker_id", "2", "--description", "e2e desc"
    )
    assert result.returncode == 0, (
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    # 出力例: "Created issue: http://localhost:3000/issues/123"
    issue_id = result.stdout.strip().rsplit("/", 1)[-1]
    assert issue_id.isdigit(), f"想定外の create 出力:\n{result.stdout}"
    return issue_id


@pytest.mark.e2e
class TestIssueList:
    """`redi issue list` は issue 一覧を表示する"""

    def test_lists_created_issue(self):
        """事前 create した subject が list に含まれる (create は正しい前提)"""
        subject = f"e2e issue list {unique_identifier('list')}"
        issue_id = _create_issue(subject)

        result = run_redi("issue", "list")
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert issue_id in result.stdout
        assert subject in result.stdout


@pytest.mark.e2e
class TestIssueView:
    """`redi issue view <id>` は指定した issue の情報を表示する"""

    def test_succeeds_for_created_issue(self):
        """create した issue を view すると subject が含まれる (create は正しい前提)"""
        subject = f"e2e issue view {unique_identifier('view')}"
        issue_id = _create_issue(subject)

        result = run_redi("issue", "view", issue_id)
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert subject in result.stdout


@pytest.mark.e2e
class TestIssueCreate:
    """`redi issue create` は新しい issue を作成する"""

    def test_creates_then_view_shows_it(self):
        """create した issue が view で取得できる (view は正しい前提)"""
        subject = f"e2e issue create {unique_identifier('create')}"
        issue_id = _create_issue(subject)

        view_result = run_redi("issue", "view", issue_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert subject in view_result.stdout


@pytest.mark.e2e
class TestIssueUpdate:
    """`redi issue update` は既存の issue を更新する"""

    def test_updates_then_view_shows_new_subject(self):
        """create→update した後 view で更新後の subject が確認できる (create/view は正しい前提)"""
        original_subject = f"e2e issue update orig {unique_identifier('update')}"
        updated_subject = f"e2e issue update new {unique_identifier('update')}"
        issue_id = _create_issue(original_subject)

        update_result = run_redi(
            "issue", "update", issue_id, "--subject", updated_subject
        )
        assert update_result.returncode == 0, (
            f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
        )

        view_result = run_redi("issue", "view", issue_id)
        assert view_result.returncode == 0, (
            f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert updated_subject in view_result.stdout
        assert original_subject not in view_result.stdout


@pytest.mark.e2e
class TestIssueDelete:
    """`redi issue delete` は指定した issue を削除する"""

    def test_deletes_then_view_fails(self):
        """create→delete した後 view が失敗する (create/view は正しい前提)"""
        subject = f"e2e issue delete {unique_identifier('delete')}"
        issue_id = _create_issue(subject)

        delete_result = run_redi("issue", "delete", issue_id, "-y")
        assert delete_result.returncode == 0, (
            f"stdout:\n{delete_result.stdout}\nstderr:\n{delete_result.stderr}"
        )

        view_result = run_redi("issue", "view", issue_id)
        assert view_result.returncode != 0, (
            f"削除後 view が成功してしまった\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
        assert "Issue not found" in view_result.stdout, (
            f"想定外のエラーで view が失敗\nstdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
        )
