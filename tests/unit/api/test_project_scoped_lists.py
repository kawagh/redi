"""プロジェクト配下の一覧 API が 404 / 403 を例外に変換することを確かめる。

いずれも変換が無い間は `raise_for_status()` がそのまま送出し、CLI まで
requests の例外が伝わって 100 行前後のトレースバックになっていた (github#441)。
"""

import pytest
import requests

from redi.api import file as file_module
from redi.api import issue_category as issue_category_module
from redi.api import membership as membership_module
from redi.api import search as search_module
from redi.api import time_entry as time_entry_module
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

    @pytest.mark.parametrize(
        ("module", "fetch"),
        [
            (
                time_entry_module,
                lambda project_id: time_entry_module.fetch_time_entries_page(
                    project_id=project_id
                ),
            ),
            (
                search_module,
                lambda project_id: search_module.search("redi", project_id=project_id),
            ),
        ],
        ids=["time_entry", "search"],
    )
    def test_project_optional_lists_raise_not_found_on_404(
        self, module, fetch, monkeypatch
    ):
        """プロジェクトを省略できる一覧も、指定時の 404 は存在しないプロジェクトとして伝える

        変換が無い間は `time_entry list` と `search` だけ生の 404 が出ていた (github#560)。
        """
        monkeypatch.setattr(module.client, "get", lambda *a, **kw: _response(404))

        with pytest.raises(ProjectNotFoundException) as e:
            fetch("nosuch")

        assert e.value.project_id == "nosuch"

    @pytest.mark.parametrize(
        ("module", "fetch"),
        [
            (
                time_entry_module,
                lambda: time_entry_module.fetch_time_entries_page(),
            ),
            (search_module, lambda: search_module.search("redi")),
        ],
        ids=["time_entry", "search"],
    )
    def test_project_optional_lists_leave_404_without_project(
        self, module, fetch, monkeypatch
    ):
        """プロジェクト未指定の 404 はプロジェクト不在ではないので変換しない"""
        monkeypatch.setattr(module.client, "get", lambda *a, **kw: _response(404))

        with pytest.raises(requests.exceptions.HTTPError):
            fetch()


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
