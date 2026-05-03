import argparse

import pytest

from redi.cli.main import _build_parser


class TestProfileFlagPlacement:
    """--profile はサブコマンドの前後どちらに置いても受け付けられる"""

    @pytest.fixture
    def parser(self) -> argparse.ArgumentParser:
        return _build_parser()

    def test_before_subcommand(self, parser):
        """ルート直後の `--profile foo issue list` を受け付ける"""
        args = parser.parse_args(["--profile", "foo", "issue", "list"])

        assert args.command == "issue"
        assert args.issue_command == "list"

    def test_after_top_level_subcommand(self, parser):
        """1階層目のサブコマンドの後ろの `issue --profile foo list` を受け付ける"""
        args = parser.parse_args(["issue", "--profile", "foo", "list"])

        assert args.command == "issue"
        assert args.issue_command == "list"
        assert args.profile == "foo"

    def test_after_nested_subcommand(self, parser):
        """ネストされたサブコマンドの後ろの `issue list --profile foo` を受け付ける"""
        args = parser.parse_args(["issue", "list", "--profile", "foo"])

        assert args.command == "issue"
        assert args.issue_command == "list"
        assert args.profile == "foo"

    def test_after_nested_subcommand_with_equals(self, parser):
        """`--profile=foo` 形式もサブコマンド後ろで受け付ける"""
        args = parser.parse_args(["issue", "create", "--profile=foo"])

        assert args.command == "issue"
        assert args.issue_command == "create"
        assert args.profile == "foo"

    def test_after_resource_only_subcommand(self, parser):
        """ネストの無い `tracker --profile foo` のような呼び出しも受け付ける"""
        args = parser.parse_args(["tracker", "--profile", "foo"])

        assert args.command == "tracker"
        assert args.profile == "foo"
