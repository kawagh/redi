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
    """呼ばれたときの refresh を received に積む fetch を返す"""

    def _fetch(refresh: bool):
        received.append(refresh)
        return [{"id": 1, "name": "バグ"}]

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
            query_service.project_api,
            "fetch_projects",
            lambda: [{"id": 3, "name": "redi_df"}],
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

        assert capsys.readouterr().out == (
            f"8 バグOR機能 {messages.query_list_private} redi_df\n4 ウォッチ redi_df\n"
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
