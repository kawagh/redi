import pytest
import requests

from redi.api import project as project_module
from redi.api.exceptions import (
    ProjectNotFoundException,
    ProjectPermissionDeniedException,
)
from redi.api.project import PROJECTS_PAGE_LIMIT


def _response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = b""
    return response


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self._payload


def _projects(start: int, count: int) -> list[dict]:
    return [{"id": i, "name": f"p{i}"} for i in range(start, start + count)]


class TestFetchProject:
    """fetch_project は HTTP のステータスコードを例外に変換する"""

    def test_raises_not_found_on_404(self, monkeypatch):
        """404 は存在しないプロジェクトとして送出する"""
        monkeypatch.setattr(
            project_module.client, "get", lambda *args, **kwargs: _response(404)
        )

        with pytest.raises(ProjectNotFoundException) as exc_info:
            project_module.fetch_project("152")

        assert exc_info.value.project_id == "152"

    def test_raises_permission_denied_on_403(self, monkeypatch):
        """403 は参照できないプロジェクト(アーカイブ済み含む)として送出する"""
        monkeypatch.setattr(
            project_module.client, "get", lambda *args, **kwargs: _response(403)
        )

        with pytest.raises(ProjectPermissionDeniedException) as exc_info:
            project_module.fetch_project("152")

        assert exc_info.value.project_id == "152"


class TestFetchProjectsPaging:
    """fetch_projects は limit / offset 未指定なら、既定の件数で打ち切らず全件返す"""

    def test_follows_total_count(self, monkeypatch):
        """total_count に届くまで offset を進めて全件返す"""
        pages = [
            FakeResponse(
                {"projects": _projects(1, PROJECTS_PAGE_LIMIT), "total_count": 150}
            ),
            FakeResponse({"projects": _projects(101, 50), "total_count": 150}),
        ]
        offsets: list[int] = []

        def fake_get(path: str, **kwargs) -> FakeResponse:
            offsets.append(kwargs["params"]["offset"])
            return pages[len(offsets) - 1]

        monkeypatch.setattr(project_module.client, "get", fake_get)

        projects = project_module.fetch_projects()

        assert offsets == [0, PROJECTS_PAGE_LIMIT]
        assert len(projects) == 150


class TestFetchProjectsExplicitPaging:
    """limit / offset を指定したときは、その1ページだけを返す"""

    @pytest.mark.parametrize(
        ("kwargs", "expected"),
        [
            ({"limit": 5}, {"limit": 5}),
            ({"offset": 10}, {"offset": 10}),
            ({"limit": 5, "offset": 10}, {"limit": 5, "offset": 10}),
        ],
        ids=["limit", "offset", "both"],
    )
    def test_takes_one_page(self, monkeypatch, kwargs, expected):
        """指定された分だけを送り、total_count が残っていても追わない"""
        calls: list[dict] = []

        def fake_get(path: str, **get_kwargs) -> FakeResponse:
            calls.append(get_kwargs["params"])
            return FakeResponse({"projects": _projects(1, 5), "total_count": 150})

        monkeypatch.setattr(project_module.client, "get", fake_get)

        projects = project_module.fetch_projects(**kwargs)

        assert calls == [expected]
        assert len(projects) == 5
