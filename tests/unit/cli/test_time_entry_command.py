import argparse

import pytest

from redi.cli.time_entry_command import add_time_entry_parser


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    add_time_entry_parser(subparsers, [])
    return parser


class TestDateFilterOption:
    """`--from` / `--to` は実在する YYYY-MM-DD だけを受け付ける"""

    @pytest.mark.parametrize(
        "argv",
        [
            ["time_entry", "--from", "2026-07-01", "list"],
            ["time_entry", "list", "--from", "2026-07-01"],
        ],
    )
    def test_valid_date_is_accepted(self, argv: list[str]):
        """有効な日付は前置・後置のどちらでも from_date に入る"""
        args = _parser().parse_args(argv)

        assert args.from_date == "2026-07-01"

    def test_surrounding_whitespace_is_stripped(self):
        """前後の空白は取り除いて渡す"""
        args = _parser().parse_args(["time_entry", "--to", " 2026-07-01 ", "list"])

        assert args.to_date == "2026-07-01"

    @pytest.mark.parametrize(
        "argv",
        [
            ["time_entry", "--from", "abc", "list"],
            ["time_entry", "--to", "2026-99-99", "list"],
            ["time_entry", "--from", "2026/07/01", "list"],
            ["time_entry", "--from", "20260701", "list"],
            ["time_entry", "list", "--from", "abc"],
            ["time_entry", "list", "--to", "2026-99-99"],
        ],
    )
    def test_invalid_date_exits_with_usage_error(self, argv: list[str]):
        """不正な日付は全件を返さず、argparse の使用方法エラー(終了コード2)で落とす"""
        with pytest.raises(SystemExit) as e:
            _parser().parse_args(argv)

        assert e.value.code == 2
