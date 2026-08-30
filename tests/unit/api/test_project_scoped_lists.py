"""プロジェクト配下の一覧 API が 404 / 403 を例外に変換することを確かめる。

いずれも変換が無い間は `raise_for_status()` がそのまま送出し、CLI まで
requests の例外が伝わって 100 行前後のトレースバックになっていた (github#441)。
"""

import pytest
import requests

from redi.api import file as file_module
from redi.api import issue_category as issue_category_module
from redi.api import membership as membership_module
from redi.api import version as version_module
from redi.api import wiki as wiki_module
from redi.api.exceptions import (
    ProjectNotFoundException,
    ProjectPermissionDeniedException,
)

FETCHERS = [
    (version_module, version_module.fetch_versions),
    (issue_category_module, issue_category_module.fetch_issue_categories),
    (membership_module, membership_module.fetch_memberships),
    (wiki_module, wiki_module.fetch_wikis),
    (file_module, file_module.fetch_files),
]


def _response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = b""
    return response


class TestProjectNotFound:
    """プロジェクト配下の一覧は 404 を ProjectNotFoundException にする"""

    @pytest.mark.parametrize(
        ("module", "fetch"), FETCHERS, ids=lambda v: getattr(v, "__name__", "")
    )
    def test_raises_not_found_on_404(self, module, fetch, monkeypatch):
        """存在しないプロジェクトを指したことが呼び出し元に伝わる"""
        monkeypatch.setattr(module.client, "get", lambda *a, **kw: _response(404))

        with pytest.raises(ProjectNotFoundException) as e:
            fetch("nosuch")

        assert e.value.project_id == "nosuch"


class TestProjectFilesPermission:
    """ファイル一覧はモジュール無効/権限不足の 403 も例外にする"""

    def test_raises_permission_denied_on_403(self, monkeypatch):
        """Redmine はファイルモジュールが無効なプロジェクトにも 403 を返す"""
        monkeypatch.setattr(file_module.client, "get", lambda *a, **kw: _response(403))

        with pytest.raises(ProjectPermissionDeniedException) as e:
            file_module.fetch_files("1")

        assert e.value.project_id == "1"

    @pytest.mark.parametrize(
        ("module", "fetch"),
        [(m, f) for m, f in FETCHERS if m is not file_module],
        ids=lambda v: getattr(v, "__name__", ""),
    )
    def test_other_lists_leave_403_to_the_caller(self, module, fetch, monkeypatch):
        """ファイル以外は 403 の意味が定まらないので変換しない"""
        monkeypatch.setattr(module.client, "get", lambda *a, **kw: _response(403))

        with pytest.raises(requests.exceptions.HTTPError):
            fetch("1")
