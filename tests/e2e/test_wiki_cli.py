import json

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
