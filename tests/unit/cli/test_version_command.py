import argparse
import json

import pytest

from redi import config
from redi.api.version import VersionNotFoundException
from redi.cli import version_command
from redi.cli.version_command import add_version_parser, handle_version
from redi.i18n import messages

VERSION = {
    "id": 1,
    "project": {"id": 2, "name": "デモ"},
    "name": "v1.0",
    "description": "説明",
    "status": "open",
    "due_date": "2026-12-31",
    "sharing": "none",
    "wiki_page_title": None,
    "created_on": "2026-08-17T00:00:00Z",
    "updated_on": "2026-08-17T00:00:00Z",
}


def parse_version_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_version_parser(parser.add_subparsers(dest="command"), [])
    return parser.parse_args(argv)


@pytest.fixture
def stub_version_service(monkeypatch):
    """service 層を差し替え、更新・削除の呼び出しを記録する。

    Redmine に値が正しく届くかは E2E (`tests/e2e/test_version_cli.py`) で見る。
    """

    calls: list[dict] = []

    def fake_read_version(version_id):
        if version_id != str(VERSION["id"]):
            raise VersionNotFoundException(version_id)
        return VERSION

    def fake_update_version(**kwargs):
        calls.append(kwargs)

    def fake_delete_version(version_id):
        fake_read_version(version_id)
        calls.append({"deleted": version_id})

    monkeypatch.setattr(
        version_command.version_service, "read_version", fake_read_version
    )
    monkeypatch.setattr(
        version_command.version_service, "update_version", fake_update_version
    )
    monkeypatch.setattr(
        version_command.version_service, "delete_version", fake_delete_version
    )
    monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")
    return calls


class TestVersionView:
    """`version view` の標準出力"""

    def test_prints_summary_and_fields(self, stub_version_service, capsys):
        """既定では id / 名前 / 状態 / URL と設定済みのフィールドを出す"""
        handle_version(parse_version_args(["version", "view", "1"]))

        out = capsys.readouterr().out
        assert "1 v1.0 (open) http://localhost:3001/versions/1" in out
        assert "2026-12-31" in out
        assert "説明" in out

    def test_full_prints_json(self, stub_version_service, capsys):
        """--full では取得した JSON だけを出す"""
        handle_version(parse_version_args(["version", "view", "1", "--full"]))

        assert json.loads(capsys.readouterr().out) == VERSION

    def test_not_found_exits(self, stub_version_service, capsys):
        """存在しない id なら見つからない旨を出して exit 1"""
        with pytest.raises(SystemExit) as e:
            handle_version(parse_version_args(["version", "view", "404"]))

        assert e.value.code == 1
        assert "404" in capsys.readouterr().err


class TestVersionUpdate:
    """`version update` が更新を送る条件"""

    def test_no_update_fields_does_not_call_api(
        self, stub_version_service, monkeypatch, capsys
    ):
        """対話入力の結果が全て空なら API を呼ばずに終了する"""

        def fill_with_empty(args):
            args.name = ""

        monkeypatch.setattr(
            version_command, "_interactive_fill_version_update_args", fill_with_empty
        )

        with pytest.raises(SystemExit) as e:
            handle_version(parse_version_args(["version", "update", "1"]))

        assert e.value.code is None
        assert stub_version_service == []
        assert messages.update_canceled in capsys.readouterr().out

    def test_empty_description_clears_value(self, stub_version_service):
        """--description "" は値を消す指定として送る"""
        handle_version(parse_version_args(["version", "update", "1", "-d", ""]))

        assert stub_version_service == [
            {
                "version_id": "1",
                "name": None,
                "status": None,
                "due_date": None,
                "description": "",
                "sharing": None,
            }
        ]

    def test_not_found_exits(self, stub_version_service, monkeypatch, capsys):
        """存在しない id なら見つからない旨を出して exit 1"""

        def fake_update_version(**kwargs):
            raise VersionNotFoundException(kwargs["version_id"])

        monkeypatch.setattr(
            version_command.version_service, "update_version", fake_update_version
        )

        with pytest.raises(SystemExit) as e:
            handle_version(parse_version_args(["version", "update", "404", "-n", "v2"]))

        assert e.value.code == 1
        assert "404" in capsys.readouterr().err


class TestVersionDelete:
    """`version delete` の確認と結果表示"""

    def test_deletes_with_yes(self, stub_version_service, capsys):
        """-y なら確認せずに削除する"""
        handle_version(parse_version_args(["version", "delete", "1", "-y"]))

        assert stub_version_service == [{"deleted": "1"}]
        assert "1" in capsys.readouterr().out

    def test_not_found_exits(self, stub_version_service, capsys):
        """存在しない id なら見つからない旨を出して exit 1"""
        with pytest.raises(SystemExit) as e:
            handle_version(parse_version_args(["version", "delete", "404", "-y"]))

        assert e.value.code == 1
        assert stub_version_service == []
        assert "404" in capsys.readouterr().err
