import argparse

import pytest

from redi.cli import main as main_module
from redi.cli.main import build_redi_parser


@pytest.fixture
def parser(monkeypatch) -> argparse.ArgumentParser:
    monkeypatch.setattr(main_module, "list_profile_names", list)
    return build_redi_parser()


class TestHyphenPrefixedPositional:
    """`-` で始まる位置引数が短オプションに黙って食われるのを弾く"""

    def test_errors_instead_of_dropping_subject(self, parser, capsys):
        """短オプションに食われる件名は、その引数を示して弾く"""
        with pytest.raises(SystemExit):
            parser.parse_args(
                ["issue", "create", "-d で始まるタイトル", "--description", "本文"]
            )

        message = capsys.readouterr().err
        assert "-d で始まるタイトル" in message
        assert "--" in message

    def test_errors_for_other_subcommands(self, parser, capsys):
        """issue 以外の位置引数を持つサブコマンドでも同じように弾く"""
        with pytest.raises(SystemExit):
            parser.parse_args(["news", "create", "-d で始まるタイトル"])

        assert "-d で始まるタイトル" in capsys.readouterr().err

    def test_accepts_positional_after_double_dash(self, parser):
        """オプションを先に書いた上で `--` の後ろに置けば件名として渡る"""
        args = parser.parse_args(
            ["issue", "create", "--description", "本文", "--", "-d で始まるタイトル"]
        )

        assert args.subject == "-d で始まるタイトル"
        assert args.description == "本文"

    def test_accepts_unregistered_short_option_like_subject(self, parser):
        """短オプションに使われていない文字で始まる件名はそのまま通る"""
        args = parser.parse_args(["issue", "create", "-x 未知オプション"])

        assert args.subject == "-x 未知オプション"

    def test_accepts_long_option_like_subject(self, parser):
        """長オプションは `=` でしか値を繋げないので件名として通る"""
        args = parser.parse_args(["issue", "create", "--tui を検証"])

        assert args.subject == "--tui を検証"

    def test_accepts_concatenated_short_option_value(self, parser):
        """空白を含まない `-dVALUE` は短オプションの値として通る"""
        args = parser.parse_args(["issue", "create", "タイトル", "-d本文"])

        assert args.subject == "タイトル"
        assert args.description == "本文"

    def test_accepts_short_option_value_joined_with_equal(self, parser):
        """`-d=VALUE` は値であることが明示されているので空白を含んでも通る"""
        args = parser.parse_args(["issue", "create", "タイトル", "-d=本文 です"])

        assert args.description == "本文 です"

    def test_accepts_separated_short_option_value(self, parser):
        """空白で区切った `-d VALUE` はこれまでどおり通る"""
        args = parser.parse_args(["issue", "create", "タイトル", "-d", "本文 です"])

        assert args.description == "本文 です"
