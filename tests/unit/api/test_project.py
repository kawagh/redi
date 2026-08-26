import pytest
import requests

from redi.api import project as project_module
from redi.api.exceptions import (
    ProjectNotFoundException,
    ProjectPermissionDeniedException,
)


def _response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = b""
    return response


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
