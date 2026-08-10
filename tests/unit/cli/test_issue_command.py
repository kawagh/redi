import argparse
import os
from pathlib import Path

import pytest

from redi.cli import issue_command
from redi.cli import main as main_module
from redi.cli.issue_command import IssueUpdateArgs
from redi.cli.main import build_redi_parser


class TestIssueUpdateArgsFromNamespace:
    """IssueUpdateArgs は `issue update` のパース結果をそのまま受け取れる"""

    @pytest.fixture
    def parser(self, monkeypatch) -> argparse.ArgumentParser:
        monkeypatch.setattr(main_module, "list_profile_names", list)
        return build_redi_parser()

    def test_accepts_all_parser_dests(self, parser):
        """パーサの dest がすべてフィールドとして存在する (欠けていれば AttributeError)"""
        args = parser.parse_args(["issue", "update", "42"])

        update_args = IssueUpdateArgs.from_namespace(args)

        assert update_args.issue_id == "42"
        assert update_args.subject is None
        assert update_args.delete_relation is False

    def test_maps_renamed_dests(self, parser):
        """`--to` や `--add-watcher` など、オプション名と dest がずれる指定も載る"""
        args = parser.parse_args(
            [
                "issue",
                "update",
                "42",
                "--to",
                "43",
                "--delete-relation",
                "--add-watcher",
                "7",
                "--remove-watcher",
                "8",
                "--time_comments",
                "作業メモ",
            ]
        )

        update_args = IssueUpdateArgs.from_namespace(args)

        assert update_args.relate_to == "43"
        assert update_args.delete_relation is True
        assert update_args.add_watcher_ids == [7]
        assert update_args.remove_watcher_ids == [8]
        assert update_args.time_comments == "作業メモ"

    def test_typed_values_are_converted_by_parser(self, parser):
        """type 指定のある引数は数値として載る"""
        args = parser.parse_args(
            ["issue", "update", "42", "--done_ratio", "30", "--hours", "1.5"]
        )

        update_args = IssueUpdateArgs.from_namespace(args)

        assert update_args.done_ratio == 30
        assert update_args.hours == 1.5


class TestSaveBodyOnFailure:
    """_save_body_on_failure は本文を退避し、保存先を通知する"""

    def test_saves_non_empty_body(self, monkeypatch, capsys):
        """本文があれば一時ファイルへ保存し、パスを出力する"""
        saved: list[str] = []

        def fake_save(text: str) -> str:
            saved.append(text)
            return "/tmp/redi-test.md"

        monkeypatch.setattr(issue_command, "save_text_to_tempfile", fake_save)
        issue_command._save_body_on_failure("失われたくない本文")

        assert saved == ["失われたくない本文"]
        assert "/tmp/redi-test.md" in capsys.readouterr().out

    def test_skips_empty_body(self, monkeypatch, capsys):
        """本文が空なら保存もせず、何も出力しない"""
        called = False

        def fake_save(text: str) -> str:
            nonlocal called
            called = True
            return "x"

        monkeypatch.setattr(issue_command, "save_text_to_tempfile", fake_save)
        issue_command._save_body_on_failure("")

        assert called is False
        assert capsys.readouterr().out == ""

    def test_round_trip_with_real_helper(self):
        """実際の save_text_to_tempfile 経由で本文がファイルに残る"""
        path = issue_command.save_text_to_tempfile("round trip")
        try:
            assert Path(path).read_text() == "round trip"
        finally:
            os.unlink(path)
