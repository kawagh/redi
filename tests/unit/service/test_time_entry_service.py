from types import SimpleNamespace

import pytest

from redi.api import time_entry as time_entry_api
from redi.service import time_entry_service


@pytest.fixture
def stub_time_entry_api(monkeypatch):
    """作成 / 更新の API 呼び出しを `calls` に記録し、slug -> id の解決を差し替える。

    プロジェクトの解決は `reditest` -> `5` の 1 件だけを知っている状態にする。
    """

    calls: list[dict] = []

    def fake_resolve_project_id(project_id):
        return "5" if project_id == "reditest" else project_id

    def fake_create_time_entry(**kwargs):
        calls.append(kwargs)
        return {"id": 1, "hours": kwargs["hours"], "spent_on": "2026-08-16"}

    def fake_update_time_entry(time_entry_id, **kwargs):
        calls.append({"time_entry_id": time_entry_id, **kwargs})

    monkeypatch.setattr(
        time_entry_service, "resolve_project_id", fake_resolve_project_id
    )
    monkeypatch.setattr(time_entry_api, "create_time_entry", fake_create_time_entry)
    monkeypatch.setattr(time_entry_api, "update_time_entry", fake_update_time_entry)
    return SimpleNamespace(calls=calls)


class TestCreateTimeEntry:
    """create_time_entry が API に渡す project_id"""

    def test_project_slug_is_resolved_to_id(self, stub_time_entry_api):
        """time_entries は slug を受け付けないため数値の id に解決して渡す"""
        time_entry_service.create_time_entry(project_id="reditest", hours=1.0)

        assert stub_time_entry_api.calls[0]["project_id"] == "5"

    def test_issue_only_does_not_resolve_project(self, stub_time_entry_api):
        """project_id を指定しなければ解決せず None のまま渡す"""
        time_entry_service.create_time_entry(issue_id="1", hours=1.0)

        assert stub_time_entry_api.calls[0]["project_id"] is None


class TestUpdateTimeEntry:
    """update_time_entry が API に渡す project_id"""

    def test_project_slug_is_resolved_to_id(self, stub_time_entry_api):
        """作成と同じく数値の id に解決して渡す"""
        time_entry_service.update_time_entry("1", project_id="reditest")

        assert stub_time_entry_api.calls[0]["project_id"] == "5"
