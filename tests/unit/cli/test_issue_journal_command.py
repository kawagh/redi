import argparse

import pytest

from redi.cli.main import build_redi_parser


class TestIssueJournalParser:
    """issue_journal サブコマンドが parser に登録されている"""

    @pytest.fixture
    def parser(self) -> argparse.ArgumentParser:
        return build_redi_parser()

    def test_update_subcommand(self, parser):
        """`issue_journal update <id> <notes>` を受け付ける"""
        args = parser.parse_args(["issue_journal", "update", "42", "updated note"])

        assert args.command == "issue_journal"
        assert args.issue_journal_command == "update"
        assert args.journal_id == 42
        assert args.notes == "updated note"

    def test_update_alias(self, parser):
        """`ij u` でも update を受け付ける"""
        args = parser.parse_args(["ij", "u", "42", "note"])

        assert args.command == "ij"
        assert args.issue_journal_command == "u"
        assert args.journal_id == 42
        assert args.notes == "note"

    def test_delete_subcommand(self, parser):
        """`issue_journal delete <id>` を受け付ける"""
        args = parser.parse_args(["issue_journal", "delete", "42"])

        assert args.command == "issue_journal"
        assert args.issue_journal_command == "delete"
        assert args.journal_id == 42
        assert args.yes is False

    def test_delete_with_yes_flag(self, parser):
        """`issue_journal delete <id> -y` で確認スキップ"""
        args = parser.parse_args(["issue_journal", "delete", "42", "-y"])

        assert args.yes is True

    def test_delete_alias(self, parser):
        """`ij d` でも delete を受け付ける"""
        args = parser.parse_args(["ij", "d", "42"])

        assert args.command == "ij"
        assert args.issue_journal_command == "d"
        assert args.journal_id == 42

    @pytest.mark.parametrize(
        "argv",
        [
            ["issue_journal", "update", "abc", "note"],
            ["issue_journal", "delete", "abc"],
        ],
        ids=["update", "delete"],
    )
    def test_rejects_non_numeric_id(self, parser, argv, capsys):
        """非数値の journal_id は Redmine に送る前に argparse が弾き exit 2 する"""
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(argv)

        assert exc.value.code == 2
        assert "invalid int value" in capsys.readouterr().err
