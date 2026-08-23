"""カスタムクエリのサービス層の単体テスト。"""

from types import SimpleNamespace
from typing import cast

import pytest
import requests

from redi.api.exceptions import ProjectNotFoundException
from redi.api.project import Project
from redi.api.query import Query
from redi.service import query_service

PROJECTS = cast(
    list[Project],
    [
        {"id": 1, "name": "Alpha", "identifier": "alpha"},
        {"id": 2, "name": "Beta", "identifier": "beta"},
    ],
)

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


@pytest.fixture
def stub_project_api(monkeypatch):
    """プロジェクト一覧を `PROJECTS` で差し替え、取得の呼び出し回数を数える。"""

    state = SimpleNamespace(fetch_count=0)

    def fake_fetch_projects():
        state.fetch_count += 1
        return PROJECTS

    monkeypatch.setattr(
        query_service.project_api, "fetch_projects", fake_fetch_projects
    )
    return state


class TestResolveQueryProjectNames:
    """resolve_query_project_names はクエリの project_id を名前に解決する"""

    def test_resolves_project_ids_to_names(self, stub_project_api):
        """project_id を持つクエリの分だけ id と名前の対応を返す"""
        queries = [
            {"id": 8, "name": "バグOR機能", "project_id": 2},
            {"id": 4, "name": "ウォッチ", "project_id": None},
        ]

        assert query_service.resolve_query_project_names(queries) == {2: "Beta"}

    def test_does_not_fetch_when_no_project_query(self, stub_project_api):
        """全プロジェクト対象のクエリしか無ければプロジェクトを引かない"""
        queries = [{"id": 4, "name": "ウォッチ", "project_id": None}]

        assert query_service.resolve_query_project_names(queries) == {}
        assert stub_project_api.fetch_count == 0

    def test_fetches_projects_only_once(self, stub_project_api):
        """複数のクエリが同じ/別のプロジェクトを指しても取得は 1 回で済ませる"""
        queries = [
            {"id": 1, "name": "a", "project_id": 1},
            {"id": 2, "name": "b", "project_id": 1},
            {"id": 3, "name": "c", "project_id": 2},
        ]

        assert query_service.resolve_query_project_names(queries) == {
            1: "Alpha",
            2: "Beta",
        }
        assert stub_project_api.fetch_count == 1

    def test_returns_empty_when_fetch_fails(self, monkeypatch):
        """一覧の補足情報でしかないので、プロジェクト取得の失敗は例外にしない"""

        def failing_fetch_projects():
            raise requests.exceptions.HTTPError("403")

        monkeypatch.setattr(
            query_service.project_api, "fetch_projects", failing_fetch_projects
        )

        assert query_service.resolve_query_project_names([{"project_id": 1}]) == {}
