import argparse

import pytest

from redi.cli.main import build_redi_parser


class TestAttachmentParser:
    """attachment サブコマンドの id は CLI の境界で int に揃える"""

    @pytest.fixture
    def parser(self) -> argparse.ArgumentParser:
        return build_redi_parser()

    @pytest.mark.parametrize(
        "argv",
        [
            ["attachment", "view", "42"],
            ["attachment", "download", "42"],
            ["attachment", "update", "42", "--filename", "a.txt"],
            ["attachment", "delete", "42"],
        ],
        ids=["view", "download", "update", "delete"],
    )
    def test_id_is_int(self, parser, argv):
        """attachment_id は int で受ける"""
        args = parser.parse_args(argv)

        assert args.attachment_id == 42

    @pytest.mark.parametrize(
        "argv",
        [
            ["attachment", "view", "abc"],
            ["attachment", "download", "abc"],
            ["attachment", "update", "abc", "--filename", "a.txt"],
            ["attachment", "delete", "abc"],
        ],
        ids=["view", "download", "update", "delete"],
    )
    def test_rejects_non_numeric_id(self, parser, argv, capsys):
        """非数値の attachment_id は Redmine に送る前に argparse が弾き exit 2 する"""
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(argv)

        assert exc.value.code == 2
        assert "invalid int value" in capsys.readouterr().err
