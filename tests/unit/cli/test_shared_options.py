import argparse

import pytest

from redi.cli.shared_options import (
    FORMAT_JSON,
    FORMAT_PLAIN,
    add_format_options,
    resolve_format,
    wants_json,
)


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_format_options(parser)
    return parser.parse_args(argv)


class TestResolveFormat:
    """`--format` と別名の `--full` から出力形式を決める"""

    def test_defaults_to_plain(self):
        """どちらも未指定なら plain"""
        assert resolve_format(_parse([])) == FORMAT_PLAIN

    def test_format_json(self):
        """`--format json` で json になる"""
        assert resolve_format(_parse(["--format", "json"])) == FORMAT_JSON

    def test_format_plain(self):
        """`--format plain` で plain になる"""
        assert resolve_format(_parse(["--format", "plain"])) == FORMAT_PLAIN

    def test_full_is_alias_of_format_json(self):
        """`--full` は `--format json` の別名として扱う"""
        assert resolve_format(_parse(["--full"])) == FORMAT_JSON

    def test_format_wins_over_full(self):
        """両方指定されたら形式を直接示す `--format` を優先する"""
        assert resolve_format(_parse(["--format", "plain", "--full"])) == FORMAT_PLAIN

    def test_rejects_unknown_format(self):
        """未対応の形式は受け付けない"""
        with pytest.raises(SystemExit):
            _parse(["--format", "tsv"])

    def test_missing_attributes_fall_back_to_plain(self):
        """`--format` も `--full` も持たない namespace でも plain を返す"""
        assert resolve_format(argparse.Namespace()) == FORMAT_PLAIN


class TestWantsJson:
    """wants_json は出力形式が json かどうかを返す"""

    @pytest.mark.parametrize(
        ("argv", "expected"),
        [
            ([], False),
            (["--full"], True),
            (["--format", "json"], True),
            (["--format", "plain"], False),
        ],
    )
    def test_returns_whether_json(self, argv, expected):
        """json のときだけ True"""
        assert wants_json(_parse(argv)) is expected
