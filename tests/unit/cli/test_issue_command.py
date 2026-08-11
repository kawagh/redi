import argparse
import os
from pathlib import Path

from redi.cli import issue_command
from redi.cli.issue_command import IssueCreateArgs, IssueUpdateArgs, add_issue_parser


def parse_issue_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_issue_parser(parser.add_subparsers(dest="command"), [])
    return parser.parse_args(argv)


class TestIssueUpdateArgsFromNamespace:
    def test_accepts_parser_output(self):
        """`issue update` のパース結果をそのまま受け取れる

        フィールド名が dest からずれていれば AttributeError で落ちる。
        `--to` と `--add-watcher` は明示的な dest 指定があり、特にずれやすい。
        """
        args = parse_issue_args(
            ["issue", "update", "42", "--to", "43", "--add-watcher", "7"]
        )

        update_args = IssueUpdateArgs.from_namespace(args)

        assert update_args.issue_id == "42"
        assert update_args.relate_to == "43"
        assert update_args.add_watcher_ids == [7]


class TestIssueCreateArgsFromNamespace:
    def test_accepts_parser_output(self):
        """`issue create` のパース結果をそのまま受け取れる

        フィールド名が dest からずれていれば AttributeError で落ちる。
        """
        args = parse_issue_args(["issue", "create", "題名", "-p", "demo"])

        create_args = IssueCreateArgs.from_namespace(args)

        assert create_args.subject == "題名"
        assert create_args.project_id == "demo"


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
