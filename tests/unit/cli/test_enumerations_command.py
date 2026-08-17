import argparse
import json

import pytest

from redi.cli import enumerations_command
from redi.i18n import messages


class TestListOutput:
    """一覧専用リソースは既定で `{id} {name}`、--full で JSON を出す"""

    @pytest.fixture(autouse=True)
    def trackers(self, monkeypatch):
        monkeypatch.setattr(
            enumerations_command,
            "fetch_trackers",
            lambda: [{"id": 1, "name": "バグ"}, {"id": 2, "name": "機能"}],
        )

    def test_default_prints_id_and_name(self, capsys):
        """既定では 1 行に id と name を出す"""
        enumerations_command.handle_tracker(argparse.Namespace(full=False))

        assert capsys.readouterr().out == "1 バグ\n2 機能\n"

    def test_full_prints_json(self, capsys):
        """--full ではレスポンスをそのまま JSON で出す"""
        enumerations_command.handle_tracker(argparse.Namespace(full=True))

        assert json.loads(capsys.readouterr().out) == [
            {"id": 1, "name": "バグ"},
            {"id": 2, "name": "機能"},
        ]


class TestCustomFieldPermission:
    """カスタムフィールドは管理者権限が無いと取得できない"""

    def test_exits_when_not_admin(self, monkeypatch, capsys):
        """権限が無いとき (取得結果が None) は理由を示して終了する"""
        monkeypatch.setattr(enumerations_command, "fetch_custom_fields", lambda: None)

        with pytest.raises(SystemExit) as e:
            enumerations_command.handle_custom_field(argparse.Namespace(full=False))

        assert e.value.code == 1
        assert messages.custom_field_admin_required in capsys.readouterr().out
