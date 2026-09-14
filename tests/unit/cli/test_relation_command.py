import argparse

import pytest

from redi.cli.main import build_redi_parser


class TestRelationParser:
    """relation サブコマンドの id は CLI の境界で int に揃える"""

    @pytest.fixture
    def parser(self) -> argparse.ArgumentParser:
        return build_redi_parser()

    def test_view_id_is_int(self, parser):
        """`relation view <id>` の relation_id は int で受ける"""
        args = parser.parse_args(["relation", "view", "42"])

        assert args.relation_id == 42

    def test_rejects_non_numeric_id(self, parser, capsys):
        """非数値の relation_id は Redmine に送る前に argparse が弾き exit 2 する"""
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["relation", "view", "abc"])

        assert exc.value.code == 2
        assert "invalid int value" in capsys.readouterr().err
