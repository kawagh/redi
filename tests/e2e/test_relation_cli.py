import json
import subprocess

import pytest

from tests.e2e.utils import run_redi, unique_identifier

# バグトラッカーには必須のカスタムフィールドがあり引数だけで作成できないため、機能トラッカーを使う
FEATURE_TRACKER_ID = "2"


def _create_issue(subject: str) -> str:
    """イシューを作成して id を返す。"""
    created = json.loads(
        run_redi(
            "issue",
            "create",
            subject,
            "--project_id",
            "reditest",
            "--tracker_id",
            FEATURE_TRACKER_ID,
            "-d",
            "e2e relation body",
            "--full",
        ).stdout
    )
    return str(created["id"])


def _create_related_issues() -> tuple[str, str]:
    """関係性で結んだ 2 つのイシューを作り、(from_id, to_id) を返す。"""
    from_id = _create_issue(unique_identifier("e2e-relation-from"))
    to_id = _create_issue(unique_identifier("e2e-relation-to"))
    run_redi("issue", "update", from_id, "--relate", "relates", "--to", to_id)
    return from_id, to_id


def _relation_id(issue_id: str) -> str:
    """イシューに紐づく最初の関係性の id を返す。"""
    issue = json.loads(run_redi("issue", "view", issue_id, "--full").stdout)
    return str(issue["relations"][0]["id"])


@pytest.mark.e2e
class TestRelationCreate:
    """`redi issue update --relate` は関係性を作成する"""

    def test_created_relation_is_shown_in_issue_view(self):
        """作成した関係性は両方のイシューの詳細表示に出る"""
        from_id, to_id = _create_related_issues()

        assert f"/issues/{to_id}" in run_redi("issue", "view", from_id).stdout
        assert f"/issues/{from_id}" in run_redi("issue", "view", to_id).stdout

    def test_exits_with_error_for_missing_related_issue(self):
        """存在しないイシューを --to に渡したら見つからないと伝えて exit 1 で終わる"""
        # Redmine の 422 は "Related issue cannot be blank" で、--to に値を渡して
        # いないように読めてしまう
        from_id = _create_issue(unique_identifier("e2e-relation-missing-to"))
        missing_id = "99999999"

        with pytest.raises(subprocess.CalledProcessError) as relate_error_info:
            run_redi(
                "issue", "update", from_id, "--relate", "relates", "--to", missing_id
            )

        relate_error = relate_error_info.value
        assert relate_error.returncode == 1
        assert f"Related issue not found: #{missing_id}" in relate_error.stdout, (
            f"想定外のエラーで relate が失敗\n"
            f"stdout:\n{relate_error.stdout}\nstderr:\n{relate_error.stderr}"
        )


@pytest.mark.e2e
class TestRelationView:
    """`redi relation view` は関係性の詳細を表示する"""

    def test_shows_both_issues(self):
        """関係性が結ぶ 2 つのイシューが出る"""
        from_id, to_id = _create_related_issues()

        viewed = run_redi("relation", "view", _relation_id(from_id)).stdout

        assert f"#{from_id} --[relates]--> #{to_id}" in viewed
        assert f"/issues/{from_id}" in viewed
        assert f"/issues/{to_id}" in viewed

    def test_exits_with_error_for_missing_relation(self):
        """存在しない関係性の表示は見つからないと伝えて exit 1 で終わる"""
        from_id, to_id = _create_related_issues()
        relation_id = _relation_id(from_id)
        run_redi("issue", "update", from_id, "--delete-relation", "--to", to_id)

        with pytest.raises(subprocess.CalledProcessError) as view_error_info:
            run_redi("relation", "view", relation_id)

        view_error = view_error_info.value
        assert view_error.returncode == 1
        assert f"Relation not found: #{relation_id}" in view_error.stderr, (
            f"想定外のエラーで view が失敗\n"
            f"stdout:\n{view_error.stdout}\nstderr:\n{view_error.stderr}"
        )


@pytest.mark.e2e
class TestRelationDelete:
    """`redi issue update --delete-relation` は関係性を削除する"""

    def test_deleted_relation_disappears_from_issue_view(self):
        """削除した関係性はイシューの詳細表示から消える"""
        from_id, to_id = _create_related_issues()

        run_redi("issue", "update", from_id, "--delete-relation", "--to", to_id)

        assert f"/issues/{to_id}" not in run_redi("issue", "view", from_id).stdout

    def test_exits_with_error_for_missing_relation(self):
        """関係性の無いイシュー間の削除は見つからないと伝えて exit 1 で終わる"""
        from_id = _create_issue(unique_identifier("e2e-relation-unrelated-from"))
        to_id = _create_issue(unique_identifier("e2e-relation-unrelated-to"))

        with pytest.raises(subprocess.CalledProcessError) as delete_error_info:
            run_redi("issue", "update", from_id, "--delete-relation", "--to", to_id)

        delete_error = delete_error_info.value
        assert delete_error.returncode == 1
        assert f"No relation found between #{from_id} and #{to_id}" in (
            delete_error.stderr
        ), (
            f"想定外のエラーで delete-relation が失敗\n"
            f"stdout:\n{delete_error.stdout}\nstderr:\n{delete_error.stderr}"
        )
