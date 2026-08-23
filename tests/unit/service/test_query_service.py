"""カスタムクエリのサービス層の単体テスト。"""

from typing import cast

from redi.api.query import Query
from redi.service import query_service

QUERIES = cast(
    list[Query],
    [
        {"id": 1, "name": "global", "is_public": True, "project_id": None},
        {"id": 2, "name": "alpha only", "is_public": True, "project_id": 1},
        {"id": 3, "name": "beta only", "is_public": False, "project_id": 2},
    ],
)


class TestListQueriesForProject:
    """list_queries_for_project() はそのプロジェクトで使えるクエリだけ返す"""

    def test_includes_project_and_global_queries(self, monkeypatch):
        """プロジェクト固有とグローバルを返し、他プロジェクトのものは外す"""
        monkeypatch.setattr(query_service, "list_queries", lambda: QUERIES)

        result = query_service.list_queries_for_project("1")

        assert [q["id"] for q in result] == [1, 2]

    def test_returns_global_only_when_project_is_none(self, monkeypatch):
        """プロジェクト未指定ならグローバルクエリのみ返す"""
        monkeypatch.setattr(query_service, "list_queries", lambda: QUERIES)

        result = query_service.list_queries_for_project(None)

        assert [q["id"] for q in result] == [1]
