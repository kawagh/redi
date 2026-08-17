import argparse
import json

import pytest

from redi.api.issue_category import IssueCategoryNotFoundException
from redi.cli.issue_category_command import (
    add_issue_category_parser,
    handle_issue_category,
)
from redi.service import issue_category_service

CATEGORIES = [
    {"id": 1, "name": "バグ", "assigned_to": {"id": 5, "name": "担当者"}},
    {"id": 2, "name": "改善"},
]


def parse_issue_category_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_issue_category_parser(parser.add_subparsers(dest="command"), [])
    return parser.parse_args(argv)


@pytest.fixture
def stub_issue_category_service(monkeypatch):
    """service を差し替え、更新系の呼び出しを `calls` に記録する。

    `CATEGORIES` を存在するカテゴリとして扱い、含まれない id は
    IssueCategoryNotFoundException にする。
    """

    calls: list[dict] = []

    def fake_list(project_id):
        return CATEGORIES

    def fake_read(category_id):
        for category in CATEGORIES:
            if str(category["id"]) == category_id:
                return {**category, "project": {"id": 1, "name": "demo"}}
        raise IssueCategoryNotFoundException(category_id)

    def fake_update(category_id, name=None, assigned_to_id=None):
        calls.append(
            {
                "category_id": category_id,
                "name": name,
                "assigned_to_id": assigned_to_id,
            }
        )

    def fake_delete(category_id, reassign_to_id=None):
        calls.append({"category_id": category_id, "reassign_to_id": reassign_to_id})

    monkeypatch.setattr(issue_category_service, "list_issue_categories", fake_list)
    monkeypatch.setattr(issue_category_service, "read_issue_category", fake_read)
    monkeypatch.setattr(issue_category_service, "update_issue_category", fake_update)
    monkeypatch.setattr(issue_category_service, "delete_issue_category", fake_delete)
    return calls


class TestIssueCategoryList:
    """`issue_category list` の標準出力"""

    def test_prints_assigned_to(self, stub_issue_category_service, capsys):
        """デフォルト担当者があれば id と name を添える"""
        handle_issue_category(
            parse_issue_category_args(["issue_category", "list", "-p", "demo"])
        )

        assert capsys.readouterr().out.splitlines() == [
            "1 バグ [5 担当者]",
            "2 改善",
        ]

    def test_full_prints_json(self, stub_issue_category_service, capsys):
        """--full では取得した JSON だけを出す"""
        handle_issue_category(
            parse_issue_category_args(
                ["issue_category", "list", "-p", "demo", "--full"]
            )
        )

        assert json.loads(capsys.readouterr().out) == CATEGORIES


class TestIssueCategoryView:
    """`issue_category view` の標準出力"""

    def test_prints_id_and_name(self, stub_issue_category_service, capsys):
        """既定ではカテゴリの id と name を出す"""
        handle_issue_category(
            parse_issue_category_args(["issue_category", "view", "1"])
        )

        assert capsys.readouterr().out.splitlines()[0] == "1 バグ"

    def test_missing_category_exits_1(self, stub_issue_category_service):
        """存在しないカテゴリは exit 1 にする"""
        with pytest.raises(SystemExit) as e:
            handle_issue_category(
                parse_issue_category_args(["issue_category", "view", "999"])
            )

        assert e.value.code == 1


class TestIssueCategoryUpdate:
    """`issue_category update` の更新項目の扱い"""

    def test_no_field_does_not_call_service(self, stub_issue_category_service):
        """更新項目が1つも無ければ service を呼ばずに終了する"""
        with pytest.raises(SystemExit):
            handle_issue_category(
                parse_issue_category_args(["issue_category", "update", "1"])
            )

        assert stub_issue_category_service == []

    def test_passes_given_fields(self, stub_issue_category_service):
        """指定した項目だけを service に渡す"""
        handle_issue_category(
            parse_issue_category_args(
                ["issue_category", "update", "1", "--name", "不具合"]
            )
        )

        assert stub_issue_category_service == [
            {"category_id": "1", "name": "不具合", "assigned_to_id": None}
        ]


class TestIssueCategoryDelete:
    """`issue_category delete` の付け替え先の扱い"""

    def test_passes_reassign_to_id(self, stub_issue_category_service):
        """--reassign_to_id を service に渡す"""
        handle_issue_category(
            parse_issue_category_args(
                ["issue_category", "delete", "1", "--reassign_to_id", "2", "-y"]
            )
        )

        assert stub_issue_category_service == [
            {"category_id": "1", "reassign_to_id": 2}
        ]

    def test_missing_category_exits_1(self, stub_issue_category_service):
        """削除確認のための取得で存在しなければ exit 1 にする"""
        with pytest.raises(SystemExit) as e:
            handle_issue_category(
                parse_issue_category_args(["issue_category", "delete", "999"])
            )

        assert e.value.code == 1
        assert stub_issue_category_service == []
