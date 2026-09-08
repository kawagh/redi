import argparse

import pytest

from redi.cli.shared_options import (
    OutputFormat,
    add_format_options,
    resolve_format,
    resolve_list_format,
    wants_json,
)
from redi.i18n import messages


def _parse(argv: list[str], *, tsv: bool = False) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_format_options(parser, tsv=tsv)
    return parser.parse_args(argv)


class TestResolveFormat:
    """`--format` と別名の `--full` から出力形式を決める"""

    def test_defaults_to_plain(self):
        """どちらも未指定なら plain"""
        assert resolve_format(_parse([])) == OutputFormat.PLAIN

    def test_format_json(self):
        """`--format json` で json になる"""
        assert resolve_format(_parse(["--format", "json"])) == OutputFormat.JSON

    def test_format_plain(self):
        """`--format plain` で plain になる"""
        assert resolve_format(_parse(["--format", "plain"])) == OutputFormat.PLAIN

    def test_full_is_alias_of_format_json(self):
        """`--full` は `--format json` の別名として扱う"""
        assert resolve_format(_parse(["--full"])) == OutputFormat.JSON

    def test_format_wins_over_full(self):
        """両方指定されたら形式を直接示す `--format` を優先する"""
        assert (
            resolve_format(_parse(["--format", "plain", "--full"]))
            == OutputFormat.PLAIN
        )

    def test_returns_enum(self):
        """戻り値は文字列ではなく OutputFormat"""
        assert isinstance(resolve_format(_parse(["--format", "json"])), OutputFormat)
        assert isinstance(resolve_format(_parse([])), OutputFormat)

    def test_rejects_unknown_format(self, capsys):
        """未対応の形式は受け付けず、選べる形式を案内する"""
        with pytest.raises(SystemExit):
            _parse(["--format", "yaml"])

        err = capsys.readouterr().err
        assert "choose from" in err
        assert "plain" in err
        assert "json" in err

    def test_missing_attributes_fall_back_to_plain(self):
        """`--format` も `--full` も持たない namespace でも plain を返す"""
        assert resolve_format(argparse.Namespace()) == OutputFormat.PLAIN


class TestTsvFormat:
    """`--format tsv` は list 系 (tsv=True) のパーサだけが受け付ける"""

    def test_list_accepts_tsv(self):
        """tsv=True のパーサは `--format tsv` を受け付ける"""
        assert (
            resolve_list_format(_parse(["--format", "tsv"], tsv=True))
            == OutputFormat.TSV
        )

    def test_view_rejects_tsv(self):
        """tsv=False (view 系) のパーサは `--format tsv` を受け付けない"""
        with pytest.raises(SystemExit):
            _parse(["--format", "tsv"])

    def test_no_short_option(self):
        """短縮形 `-f` は `--firstname` / `--filename` と衝突するので付けない"""
        with pytest.raises(SystemExit):
            _parse(["-f", "tsv"], tsv=True)

    def test_wants_json_exits_on_tsv(self, capsys):
        """親パーサ経由で view 系に tsv が流れてきたら、黙って plain にせず exit 1"""
        args = _parse(["--format", "tsv"], tsv=True)

        with pytest.raises(SystemExit) as excinfo:
            wants_json(args)

        assert excinfo.value.code == 1
        assert messages.error_format_tsv_list_only in capsys.readouterr().err


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
