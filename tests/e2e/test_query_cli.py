import json

import pytest

from tests.e2e.utils import (
    GLOBAL_QUERY_NAME,
    OTHER_PROJECT_QUERY_NAME,
    PRIVATE_QUERY_NAME,
    PROJECT_QUERY_NAME,
    query_named,
    requires_e2e_profiles,
    run_redi,
    run_redi_as_developer,
)


def _queries() -> list[dict]:
    return json.loads(run_redi("query", "list", "--full").stdout)


@pytest.mark.e2e
class TestQueryList:
    """`redi query list` はシードしたカスタムクエリを返す"""

    def test_lists_seeded_queries(self):
        """シードした公開クエリが名前で引ける"""
        names = [query["name"] for query in _queries()]

        assert GLOBAL_QUERY_NAME in names
        assert PROJECT_QUERY_NAME in names
        assert OTHER_PROJECT_QUERY_NAME in names

    def test_global_query_has_no_project(self):
        """全プロジェクトで見えるクエリは project_id を持たない"""
        assert query_named(GLOBAL_QUERY_NAME)["project_id"] is None

    def test_project_query_belongs_to_its_project(self):
        """プロジェクト固有のクエリは所属プロジェクトの id を持つ"""
        reditest_id = json.loads(
            run_redi("project", "view", "reditest", "--full").stdout
        )["id"]

        assert query_named(PROJECT_QUERY_NAME)["project_id"] == reditest_id
        assert query_named(OTHER_PROJECT_QUERY_NAME)["project_id"] != reditest_id


@pytest.mark.e2e
@requires_e2e_profiles
class TestQueryVisibility:
    """`redi query list` は実行ユーザーに見えるクエリだけを返す"""

    def test_private_query_is_listed_for_its_owner(self):
        """非公開クエリは作成者 (admin) には出る"""
        assert PRIVATE_QUERY_NAME in run_redi("query", "list").stdout

    def test_private_query_is_hidden_from_other_user(self):
        """非公開クエリは作成者以外 (developer) には出ない"""
        listed = run_redi_as_developer("query", "list").stdout

        assert PRIVATE_QUERY_NAME not in listed
        assert GLOBAL_QUERY_NAME in listed
