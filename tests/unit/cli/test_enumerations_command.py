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
            lambda refresh=False: [
                {"id": 1, "name": "バグ"},
                {"id": 2, "name": "機能"},
            ],
        )

    def test_default_prints_id_and_name(self, capsys):
        """既定では 1 行に id と name を出す"""
        enumerations_command.handle_tracker(
            argparse.Namespace(full=False, refresh=False)
        )

        assert capsys.readouterr().out == "1 バグ\n2 機能\n"

    def test_full_prints_json(self, capsys):
        """--full ではレスポンスをそのまま JSON で出す"""
        enumerations_command.handle_tracker(
            argparse.Namespace(full=True, refresh=False)
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
            enumerations_command.handle_custom_field(
                argparse.Namespace(full=False, refresh=False)
            )

        assert e.value.code == 1
        assert messages.custom_field_admin_required in capsys.readouterr().out


class TestCustomFieldView:
    """`custom_field view <id>` は一覧から 1 件を絞り込んで詳細を表示する"""

    @pytest.fixture(autouse=True)
    def custom_fields(self, monkeypatch):
        monkeypatch.setattr(
            enumerations_command,
            "fetch_custom_fields",
            lambda refresh=False: [
                {
                    "id": 1,
                    "name": "ドロップダウン",
                    "description": "選べる値",
                    "customized_type": "issue",
                    "field_format": "list",
                    "regexp": "^A",
                    "min_length": 1,
                    "max_length": 10,
                    "is_required": True,
                    "default_value": "A",
                    "possible_values": [{"value": "A", "label": "A"}],
                    "trackers": [{"id": 1, "name": "バグ"}],
                    "roles": [{"id": 3, "name": "開発者"}],
                },
                # 未設定の項目を持つ、キーバリューリスト形式のカスタムフィールド
                {
                    "id": 2,
                    "name": "キーバリュー",
                    "description": "",
                    "customized_type": "issue",
                    "field_format": "enumeration",
                    "regexp": "",
                    "min_length": None,
                    "max_length": None,
                    "is_required": False,
                    "default_value": None,
                    "possible_values": [{"value": "10", "label": "高"}],
                    "trackers": [],
                    "roles": [],
                },
            ],
        )

    def _view(self, custom_field_id, full=False):
        enumerations_command.handle_custom_field(
            argparse.Namespace(
                full=full,
                refresh=False,
                custom_field_command="view",
                custom_field_id=custom_field_id,
            )
        )

    def test_prints_all_fields_of_the_specified_id(self, capsys):
        """id で指定した 1 件だけを、選択肢・トラッカー・ロールまで並べる"""
        self._view("1")

        assert (
            capsys.readouterr().out
            == "\n".join(
                [
                    "1 ドロップダウン",
                    messages.label_description_field.format(value="選べる値"),
                    messages.label_customized_type.format(value="issue"),
                    messages.label_field_format.format(value="list"),
                    messages.label_is_required.format(value=messages.label_bool_true),
                    messages.label_default_value.format(value="A"),
                    messages.label_regexp.format(value="^A"),
                    messages.label_min_length.format(value=1),
                    messages.label_max_length.format(value=10),
                    messages.label_possible_values_header,
                    "  A",
                    messages.label_trackers_header,
                    "  1 バグ",
                    messages.label_roles_header,
                    "  3 開発者",
                ]
            )
            + "\n"
        )

    def test_prints_value_with_label_and_omits_empty_fields(self, capsys):
        """キーバリューリスト形式は value と label を並べ、未設定の項目は行ごと出さない"""
        self._view("2")

        assert (
            capsys.readouterr().out
            == "\n".join(
                [
                    "2 キーバリュー",
                    messages.label_customized_type.format(value="issue"),
                    messages.label_field_format.format(value="enumeration"),
                    messages.label_is_required.format(value=messages.label_bool_false),
                    messages.label_possible_values_header,
                    "  10 高",
                ]
            )
            + "\n"
        )

    def test_full_prints_json_of_the_single_custom_field(self, capsys):
        """--full では該当する 1 件だけを JSON で出す"""
        self._view("1", full=True)

        assert json.loads(capsys.readouterr().out)["id"] == 1

    def test_exits_when_id_is_unknown(self, capsys):
        """存在しない id を指定したときは理由を示して終了する"""
        with pytest.raises(SystemExit) as e:
            self._view("99")

        assert e.value.code == 1
        assert (
            messages.custom_field_not_found.format(id="99") in capsys.readouterr().out
        )


class TestRefreshIsPassedToFetch:
    """--refresh はハンドラから fetch にそのまま渡される"""

    def test_passes_refresh_flag(self, monkeypatch):
        """args.refresh が True なら fetch も refresh=True で呼ばれる"""
        received = {}

        def _fetch(refresh=False):
            received["refresh"] = refresh
            return [{"id": 1, "name": "バグ"}]

        monkeypatch.setattr(enumerations_command, "fetch_trackers", _fetch)

        enumerations_command.handle_tracker(
            argparse.Namespace(full=False, refresh=True)
        )

        assert received["refresh"] is True
