import json

import pytest

from tests.e2e.utils import run_redi, unique_identifier


def _create_issue(subject_suffix: str) -> str:
    subject = f"e2e relation {subject_suffix} {unique_identifier('rel')}"
    create_result = run_redi(
        "issue", "create", subject, "--tracker_id", "2", "--description", "rel test"
    )
    assert create_result.returncode == 0, (
        f"stdout:\n{create_result.stdout}\nstderr:\n{create_result.stderr}"
    )
    issue_id = create_result.stdout.strip().rsplit("/", 1)[-1]
    assert issue_id.isdigit(), f"想定外の create 出力:\n{create_result.stdout}"
    return issue_id


def _create_relation(from_id: str, to_id: str) -> str:
    """from_id --[relates]--> to_id の relation を作って relation_id を返す。"""
    update_result = run_redi(
        "issue", "update", from_id, "--relate", "relates", "--to", to_id
    )
    assert update_result.returncode == 0, (
        f"stdout:\n{update_result.stdout}\nstderr:\n{update_result.stderr}"
    )

    view_result = run_redi("issue", "view", from_id, "--include", "relations", "--full")
    assert view_result.returncode == 0, (
        f"stdout:\n{view_result.stdout}\nstderr:\n{view_result.stderr}"
    )
    parsed = json.loads(view_result.stdout)
    relations = parsed.get("relations") or []
    assert relations, f"relation が紐付いていない:\n{view_result.stdout}"
    return str(relations[0]["id"])


@pytest.mark.e2e
class TestRelationView:
    """`redi relation view <id>` は指定したリレーションの情報を表示する"""

    def test_succeeds_for_existing_relation(self):
        """issue 間に作成した relation を view すると issue_id 同士のリンクが含まれる"""
        from_id = _create_issue("from")
        to_id = _create_issue("to")
        relation_id = _create_relation(from_id, to_id)

        result = run_redi("relation", "view", relation_id)
        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert f"#{from_id}" in result.stdout
        assert f"#{to_id}" in result.stdout
        assert "relates" in result.stdout

    def test_fails_for_nonexistent_relation(self):
        """存在しない relation_id を view するとエラーになる"""
        result = run_redi("relation", "view", "999999")
        assert result.returncode != 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "Relation not found" in result.stdout, (
            f"想定外のエラー\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
