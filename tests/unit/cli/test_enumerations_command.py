import argparse
import dataclasses
import json

import pytest

from redi.cli.enumerations_command import (
    ENUMERATION_RESOURCES,
    EnumerationResource,
    handle_enumeration,
)
from redi.i18n import messages
from redi.service import query_service

RESOURCES = {resource.name: resource for resource in ENUMERATION_RESOURCES}


def with_fetch(name: str, fetch) -> EnumerationResource:
    """リソース定義の fetch だけ差し替えたものを返す"""
    return dataclasses.replace(RESOURCES[name], fetch=fetch)


def recording_fetch(received: list[bool]):
    """呼ばれたときの refresh を received に積む fetch を返す

    query の整形が is_public / project_id を参照するので、実レスポンスに揃えて
    どのリソースに差し替えても表示まで通るようにする。
    """

    def _fetch(refresh: bool):
        received.append(refresh)
        return [{"id": 1, "name": "バグ", "is_public": True, "project_id": None}]

    return _fetch


class TestListOutput:
    """一覧専用リソースは既定で `{id} {name}`、--full で JSON を出す"""

    @pytest.fixture
    def tracker(self) -> EnumerationResource:
        return with_fetch(
            "tracker",
            lambda refresh: [{"id": 1, "name": "バグ"}, {"id": 2, "name": "機能"}],
        )

    def test_default_prints_id_and_name(self, tracker, capsys):
        """既定では 1 行に id と name を出す"""
        handle_enumeration(tracker, argparse.Namespace(full=False, refresh=False))

        assert capsys.readouterr().out == "1 バグ\n2 機能\n"

    def test_full_prints_json(self, tracker, capsys):
        """--full ではレスポンスをそのまま JSON で出す"""
        handle_enumeration(tracker, argparse.Namespace(full=True, refresh=False))

        assert json.loads(capsys.readouterr().out) == [
            {"id": 1, "name": "バグ"},
            {"id": 2, "name": "機能"},
        ]


class TestQueryListOutput:
    """query は id と name に加えて公開/非公開と対象プロジェクトを出す"""

    @pytest.fixture
    def stub_projects(self, monkeypatch):
        """project_id を名前に解決するためのプロジェクト一覧を差し替える"""
        monkeypatch.setattr(
            query_service, "list_projects", lambda: [{"id": 3, "name": "redi_df"}]
        )

    def query_with(self, *queries) -> EnumerationResource:
        return with_fetch("query", lambda refresh: list(queries))

    def test_marks_private_query(self, stub_projects, capsys):
        """非公開クエリには印を付け、公開クエリには付けない"""
        resource = self.query_with(
            {"id": 8, "name": "バグOR機能", "is_public": False, "project_id": 3},
            {"id": 4, "name": "ウォッチ", "is_public": True, "project_id": 3},
        )

        handle_enumeration(resource, argparse.Namespace(full=False))

        project = messages.query_list_project.format(name="redi_df")
        assert capsys.readouterr().out == (
            f"8 バグOR機能 {messages.query_list_private} {project}\n"
            f"4 ウォッチ {project}\n"
        )

    def test_shows_all_projects_for_null_project_id(self, capsys):
        """project_id が null のクエリは全プロジェクト対象と分かる表記にする"""
        resource = self.query_with(
            {"id": 4, "name": "ウォッチ", "is_public": True, "project_id": None}
        )

        handle_enumeration(resource, argparse.Namespace(full=False))

        assert capsys.readouterr().out == (
            f"4 ウォッチ {messages.query_list_all_projects}\n"
        )

    def test_falls_back_to_project_id_when_unresolved(self, stub_projects, capsys):
        """プロジェクト名が引けなかったときは数値 id で出す"""
        resource = self.query_with(
            {"id": 8, "name": "バグOR機能", "is_public": True, "project_id": 99}
        )

        handle_enumeration(resource, argparse.Namespace(full=False))

        assert capsys.readouterr().out == (
            f"8 バグOR機能 {messages.query_list_unknown_project.format(id=99)}\n"
        )

    def test_wraps_project_name_so_query_name_boundary_is_readable(
        self, stub_projects, capsys
    ):
        """クエリ名に空白が入っても境界が読めるようプロジェクト名を括弧で括る"""
        resource = self.query_with(
            {"id": 8, "name": "バグ OR 機能", "is_public": True, "project_id": 3}
        )

        handle_enumeration(resource, argparse.Namespace(full=False))

        assert capsys.readouterr().out == (
            f"8 バグ OR 機能 {messages.query_list_project.format(name='redi_df')}\n"
        )

    def test_full_prints_json(self, capsys):
        """--full ではレスポンスをそのまま JSON で出す"""
        query = {"id": 8, "name": "バグOR機能", "is_public": False, "project_id": 3}
        resource = self.query_with(query)

        handle_enumeration(resource, argparse.Namespace(full=True))

        assert json.loads(capsys.readouterr().out) == [query]


class TestCustomFieldPermission:
    """カスタムフィールドは管理者権限が無いと取得できない"""

    def test_exits_when_not_admin(self, capsys):
        """権限が無いとき (取得結果が None) は理由を示して終了する"""
        custom_field = with_fetch("custom_field", lambda refresh: None)

        with pytest.raises(SystemExit) as e:
            handle_enumeration(
                custom_field, argparse.Namespace(full=False, refresh=False)
            )

        assert e.value.code == 1
        assert messages.custom_field_admin_required in capsys.readouterr().out


class TestCustomFieldView:
    """`custom_field view <id>` は一覧から 1 件を絞り込んで詳細を表示する"""

    @pytest.fixture
    def custom_field(self) -> EnumerationResource:
        return with_fetch(
            "custom_field",
            lambda refresh: [
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

    def _view(self, custom_field, custom_field_id, full=False):
        handle_enumeration(
            custom_field,
            argparse.Namespace(
                full=full,
                refresh=False,
                custom_field_command="view",
                custom_field_id=custom_field_id,
            ),
        )

    def test_prints_all_fields_of_the_specified_id(self, custom_field, capsys):
        """id で指定した 1 件だけを、選択肢・トラッカー・ロールまで並べる"""
        self._view(custom_field, "1")

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

    def test_prints_value_with_label_and_omits_empty_fields(self, custom_field, capsys):
        """キーバリューリスト形式は value と label を並べ、未設定の項目は行ごと出さない"""
        self._view(custom_field, "2")

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

    def test_full_prints_json_of_the_single_custom_field(self, custom_field, capsys):
        """--full では該当する 1 件だけを JSON で出す"""
        self._view(custom_field, "1", full=True)

        assert json.loads(capsys.readouterr().out)["id"] == 1

    def test_exits_when_id_is_unknown(self, custom_field, capsys):
        """存在しない id を指定したときは理由を示して終了する"""
        with pytest.raises(SystemExit) as e:
            self._view(custom_field, "99")

        assert e.value.code == 1
        assert (
            messages.custom_field_not_found.format(id="99") in capsys.readouterr().out
        )


class TestRefreshIsPassedToFetch:
    """--refresh はハンドラから fetch にそのまま渡される"""

    @pytest.mark.parametrize(
        "resource",
        [resource for resource in ENUMERATION_RESOURCES if resource.cached],
        ids=lambda resource: resource.name,
    )
    def test_passes_refresh_flag(self, resource):
        """args.refresh が True なら fetch も refresh=True で呼ばれる"""
        received: list[bool] = []
        target = dataclasses.replace(resource, fetch=recording_fetch(received))

        handle_enumeration(target, argparse.Namespace(full=False, refresh=True))

        assert received == [True]

    def test_defaults_to_false_when_option_is_absent(self):
        """--refresh を持たないリソースでは refresh=False で呼ばれる"""
        received: list[bool] = []
        query = with_fetch("query", recording_fetch(received))

        handle_enumeration(query, argparse.Namespace(full=False))

        assert received == [False]
