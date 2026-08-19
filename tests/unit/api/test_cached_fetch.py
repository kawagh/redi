import json

import pytest
import requests

from redi import cache, config
from redi.api import custom_field as custom_field_module
from redi.api import enumeration as enumeration_module
from redi.api import issue_status as issue_status_module
from redi.api import tracker as tracker_module

# (モジュール, fetch 関数名, キャッシュキー, レスポンスのキー)
CACHED_FETCHERS = [
    (tracker_module, "fetch_trackers", "trackers", "trackers"),
    (issue_status_module, "fetch_issue_statuses", "issue_statuses", "issue_statuses"),
    (custom_field_module, "fetch_custom_fields", "custom_fields", "custom_fields"),
    (
        enumeration_module,
        "fetch_issue_priorities",
        "issue_priorities",
        "issue_priorities",
    ),
    (
        enumeration_module,
        "fetch_time_entry_activities",
        "time_entry_activities",
        "time_entry_activities",
    ),
    (
        enumeration_module,
        "fetch_document_categories",
        "document_categories",
        "document_categories",
    ),
]


def _response(payload: dict) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response._content = json.dumps(payload).encode()
    return response


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(config, "redmine_url", "http://localhost:3000")
    return tmp_path


@pytest.mark.parametrize(
    ("module", "func_name", "cache_key", "response_key"),
    CACHED_FETCHERS,
    ids=[func_name for _, func_name, _, _ in CACHED_FETCHERS],
)
class TestRefresh:
    """キャッシュを持つ fetch は refresh=True でキャッシュを読まず取り直す"""

    def test_uses_cache_by_default(
        self, cache_dir, monkeypatch, module, func_name, cache_key, response_key
    ):
        """refresh 未指定ならキャッシュを返し、API を呼ばない"""
        cache.save(cache_key, [{"id": 1, "name": "キャッシュ"}])

        def _fail(*args, **kwargs):
            raise AssertionError("API を呼んではいけない")

        monkeypatch.setattr(module.client, "get", _fail)

        assert getattr(module, func_name)() == [{"id": 1, "name": "キャッシュ"}]

    def test_ignores_cache_when_refresh(
        self, cache_dir, monkeypatch, module, func_name, cache_key, response_key
    ):
        """refresh=True ならキャッシュがあっても API から取り直す"""
        cache.save(cache_key, [{"id": 1, "name": "キャッシュ"}])
        fresh = [{"id": 2, "name": "サーバ"}]
        monkeypatch.setattr(
            module.client, "get", lambda *a, **kw: _response({response_key: fresh})
        )

        assert getattr(module, func_name)(refresh=True) == fresh

    def test_refresh_updates_cache(
        self, cache_dir, monkeypatch, module, func_name, cache_key, response_key
    ):
        """refresh=True で取り直した値はキャッシュにも保存される"""
        cache.save(cache_key, [{"id": 1, "name": "キャッシュ"}])
        fresh = [{"id": 2, "name": "サーバ"}]
        monkeypatch.setattr(
            module.client, "get", lambda *a, **kw: _response({response_key: fresh})
        )

        getattr(module, func_name)(refresh=True)

        assert cache.load(cache_key) == fresh
