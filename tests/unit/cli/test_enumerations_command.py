import argparse
import json

import pytest

from redi.cli import enumerations_command
from redi.i18n import messages

RESOURCES = {r.name: r for r in enumerations_command.ENUMERATION_RESOURCES}
TRACKER = RESOURCES["tracker"]
CUSTOM_FIELD = RESOURCES["custom_field"]


class TestListOutput:
    """一覧専用リソースは既定で `{id} {name}`、--full で JSON を出す"""

    @pytest.fixture(autouse=True)
    def trackers(self, monkeypatch):
        monkeypatch.setattr(
            enumerations_command,
            "fetch_trackers",
            lambda refresh=False: [
                {"id": 1, "name": "バグ"},
                {"id": 2, "name": "機能"},
            ],
        )

    def test_default_prints_id_and_name(self, capsys):
        """既定では 1 行に id と name を出す"""
        enumerations_command.handle_enumeration(
            TRACKER, argparse.Namespace(full=False, refresh=False)
        )

        assert capsys.readouterr().out == "1 バグ\n2 機能\n"

    def test_full_prints_json(self, capsys):
        """--full ではレスポンスをそのまま JSON で出す"""
        enumerations_command.handle_enumeration(
            TRACKER, argparse.Namespace(full=True, refresh=False)
        )

        assert json.loads(capsys.readouterr().out) == [
            {"id": 1, "name": "バグ"},
            {"id": 2, "name": "機能"},
        ]


class TestCustomFieldPermission:
    """カスタムフィールドは管理者権限が無いと取得できない"""

    def test_exits_when_not_admin(self, monkeypatch, capsys):
        """権限が無いとき (取得結果が None) は理由を示して終了する"""
        monkeypatch.setattr(
            enumerations_command, "fetch_custom_fields", lambda refresh=False: None
        )

        with pytest.raises(SystemExit) as e:
            enumerations_command.handle_enumeration(
                CUSTOM_FIELD, argparse.Namespace(full=False, refresh=False)
            )

        assert e.value.code == 1
        assert messages.custom_field_admin_required in capsys.readouterr().out


class TestRefreshIsPassedToFetch:
    """--refresh はハンドラから fetch にそのまま渡される"""

    def test_passes_refresh_flag(self, monkeypatch):
        """args.refresh が True なら fetch も refresh=True で呼ばれる"""
        received = {}

        def _fetch(refresh=False):
            received["refresh"] = refresh
            return [{"id": 1, "name": "バグ"}]

        monkeypatch.setattr(enumerations_command, "fetch_trackers", _fetch)

        enumerations_command.handle_enumeration(
            TRACKER, argparse.Namespace(full=False, refresh=True)
        )

        assert received["refresh"] is True
