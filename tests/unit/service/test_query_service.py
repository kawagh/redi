from types import SimpleNamespace
from typing import cast

import pytest
import requests

from redi.api.project import Project
from redi.service import query_service

PROJECTS = cast(
    list[Project],
    [
        {"id": 1, "name": "Alpha", "identifier": "alpha"},
        {"id": 2, "name": "Beta", "identifier": "beta"},
    ],
)


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
