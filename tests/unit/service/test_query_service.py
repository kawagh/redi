"""カスタムクエリのサービス層の単体テスト。"""

from typing import cast

from redi.api.exceptions import ProjectNotFoundException
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

    def test_resolves_identifier_before_matching(self, monkeypatch):
        """identifier で指定されても数値 id に解決して突き合わせる

        config の default_project_id には identifier も書けるが、クエリが持つ
        project_id は数値なので、解決しないとプロジェクト固有のクエリを落とす。
        """
        monkeypatch.setattr(query_service, "list_queries", lambda: QUERIES)
        monkeypatch.setattr(
            query_service,
            "resolve_project_id",
            lambda value: "1" if value == "alpha" else value,
        )

        result = query_service.list_queries_for_project("alpha")

        assert [q["id"] for q in result] == [1, 2]

    def test_falls_back_to_global_when_project_is_unknown(self, monkeypatch):
        """プロジェクトを解決できなければグローバルクエリだけでも選べるようにする"""
        monkeypatch.setattr(query_service, "list_queries", lambda: QUERIES)

        def raise_not_found(value):
            raise ProjectNotFoundException(value)

        monkeypatch.setattr(query_service, "resolve_project_id", raise_not_found)

        result = query_service.list_queries_for_project("missing")

        assert [q["id"] for q in result] == [1]
