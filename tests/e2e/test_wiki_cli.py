import json
import subprocess

import pytest

from tests.e2e.utils import requires_redmine_7_0, run_redi, unique_identifier


@pytest.mark.e2e
@requires_redmine_7_0
class TestWikiPageProject:
    """`redi wiki view --full` は redmine 7.0 で追加された project を含む"""

    def test_created_page_has_project(self):
        """作成したページを取得すると所属プロジェクトが含まれる"""
        title = unique_identifier("e2e-wiki")
        run_redi("wiki", "create", title, "-d", "e2e wiki body")

        page = json.loads(run_redi("wiki", "view", title, "--full").stdout)

        assert page["project"]["name"] == "reditestプロジェクト"


@pytest.mark.e2e
class TestWikiDelete:
    """`redi wiki delete` は Wiki ページを削除する"""

    # Redmine は先頭が小文字のタイトルを大文字始まりに正規化するため、一覧の表示と
    # 突き合わせられるよう大文字始まりの識別子を使う
    def test_deleted_page_disappears_from_list(self):
        """削除したページは一覧に出てこなくなる"""
        title = unique_identifier("E2e-wiki-delete")
        run_redi("wiki", "create", title, "-d", "e2e wiki body")
        assert title in run_redi("wiki", "list").stdout

        run_redi("wiki", "delete", title, "--yes")

        assert title not in run_redi("wiki", "list").stdout

    def test_child_page_remains_after_parent_deleted(self):
        """親ページを削除しても子ページは残る (TUI の一覧更新が前提にしている)"""
        parent = unique_identifier("E2e-wiki-parent")
        child = unique_identifier("E2e-wiki-child")
        run_redi("wiki", "create", parent, "-d", "parent body")
        run_redi("wiki", "create", child, "-d", "child body", "--parent_title", parent)

        run_redi("wiki", "delete", parent, "--yes")

        listed = run_redi("wiki", "list").stdout
        assert parent not in listed
        assert child in listed

    def test_exits_with_error_for_missing_page(self):
        """存在しないページの削除は exit 1 で終わる"""
        title = unique_identifier("E2e-wiki-missing")

        with pytest.raises(subprocess.CalledProcessError) as e:
            run_redi("wiki", "delete", title, "--yes")

        assert e.value.returncode == 1
