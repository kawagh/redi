import pytest
import requests

from redi.api import issue as issue_module
from redi.api.exceptions import ProjectNotFoundException, QueryNotFoundException


def _response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = b""
    return response


class TestFetchIssuesPage:
    """fetch_issues_page は 404 を原因ごとの例外に変換する"""

    def test_raises_not_found_with_project_id(self, monkeypatch):
        """project_id 指定で 404 ならプロジェクト未検出として送出する"""
        monkeypatch.setattr(
            issue_module.client, "get", lambda *args, **kwargs: _response(404)
        )

        with pytest.raises(ProjectNotFoundException) as exc_info:
            issue_module.fetch_issues_page(project_id="2")

        assert exc_info.value.project_id == "2"

    def test_raises_query_not_found_with_query_id(self, monkeypatch):
        """query_id 指定で 404 ならクエリ未検出として送出する"""
        monkeypatch.setattr(
            issue_module.client, "get", lambda *args, **kwargs: _response(404)
        )

        with pytest.raises(QueryNotFoundException) as exc_info:
            issue_module.fetch_issues_page(query_id="5")

        assert exc_info.value.query_id == "5"

    def test_prefers_query_not_found_with_both_ids(self, monkeypatch):
        """両方指定の 404 はレスポンスから切り分けられないのでクエリ側で送出する"""
        monkeypatch.setattr(
            issue_module.client, "get", lambda *args, **kwargs: _response(404)
        )

        with pytest.raises(QueryNotFoundException):
            issue_module.fetch_issues_page(project_id="2", query_id="5")

    def test_raises_http_error_without_project_id(self, monkeypatch):
        """project_id 未指定の 404 は従来どおり HTTPError にする"""
        monkeypatch.setattr(
            issue_module.client, "get", lambda *args, **kwargs: _response(404)
        )

        with pytest.raises(requests.exceptions.HTTPError):
            issue_module.fetch_issues_page()
