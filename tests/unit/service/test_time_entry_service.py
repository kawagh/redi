from types import SimpleNamespace
from typing import cast

import pytest

from redi.api import time_entry as time_entry_api
from redi.api.time_entry import TimeEntry
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


class TestFormatTimeEntryLine:
    """format_time_entry_line が組み立てる一覧の行"""

    def _raw_entry(self) -> dict:
        return {
            "id": 72,
            "spent_on": "2026-08-16",
            "user": {"id": 1, "name": "Redmine Admin"},
            "activity": {"id": 9, "name": "開発作業"},
            "hours": 2.0,
            "issue": {"id": 152},
            "comments": "sagyou",
        }

    def _entry(self) -> TimeEntry:
        return cast(TimeEntry, self._raw_entry())

    def test_activity_name_follows_hours(self):
        """活動名を時間の直後に出す(`view` と同じ並びにする)"""
        line = time_entry_service.format_time_entry_line(self._entry())

        assert line == "72  (2026-08-16)  Redmine Admin  2.0h  開発作業  #152  sagyou"

    def test_activity_name_is_shown_without_user(self):
        """ユーザ列を出さない場合も活動名は出す"""
        line = time_entry_service.format_time_entry_line(
            self._entry(), include_user=False
        )

        assert line == "72  (2026-08-16)  2.0h  開発作業  #152  sagyou"

    def test_missing_activity_is_skipped(self):
        """activity が欠けていても落ちず、その列だけを省く"""
        raw = self._raw_entry()
        del raw["activity"]

        line = time_entry_service.format_time_entry_line(cast(TimeEntry, raw))

        assert line == "72  (2026-08-16)  Redmine Admin  2.0h  #152  sagyou"
