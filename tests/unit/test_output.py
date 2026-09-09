"""標準出力・標準エラー出力の使い分けと TSV 出力を守るテスト。"""

import pytest

from redi.output import eprint, print_tsv, tsv_cell, tsv_ref


class TestEprint:
    """eprint() の出力先"""

    def test_writes_to_stderr(self, capsys):
        """メッセージは標準エラー出力に出す"""
        eprint("boom")

        assert capsys.readouterr().err == "boom\n"

    def test_does_not_write_to_stdout(self, capsys):
        """`redi issue list > issues.txt` の結果に混ざらないよう標準出力には出さない"""
        eprint("boom")

        assert capsys.readouterr().out == ""


class TestTsvCell:
    """tsv_cell() は値を TSV の 1 セルに収める"""

    def test_none_is_empty(self):
        """None (project_id が null など) は空セルにする"""
        assert tsv_cell(None) == ""

    @pytest.mark.parametrize(("value", "expected"), [(True, "true"), (False, "false")])
    def test_bool_is_lowercase(self, value, expected):
        """bool は Redmine の JSON と同じ true / false の綴りにする"""
        assert tsv_cell(value) == expected

    def test_int_is_stringified(self):
        """数値はそのまま文字列にする"""
        assert tsv_cell(12) == "12"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("a\tb", "a b"),
            ("a\nb", "a b"),
            ("a\r\nb", "a b"),
            ("a\n\n\tb", "a b"),
        ],
    )
    def test_tabs_and_newlines_collapse_to_one_space(self, value, expected):
        """1 レコード 1 行を守るため、タブと改行は空白 1 つに潰す"""
        assert tsv_cell(value) == expected


class TestPrintTsv:
    """print_tsv() はヘッダー行 + タブ区切りの行を標準出力に出す"""

    def test_prints_header_and_rows(self, capsys):
        """先頭にヘッダー行、続けて 1 レコード 1 行を出す"""
        print_tsv(
            ("id", "name", "is_public", "project_id"),
            [(1, "ウォッチしているチケット", True, None), (2, "バグOR機能", False, 1)],
        )

        assert capsys.readouterr().out == (
            "id\tname\tis_public\tproject_id\n"
            "1\tウォッチしているチケット\ttrue\t\n"
            "2\tバグOR機能\tfalse\t1\n"
        )

    def test_header_even_when_empty(self, capsys):
        """0 件でもヘッダー行は出す (列名だけは自己記述できるようにする)"""
        print_tsv(("id", "name"), [])

        assert capsys.readouterr().out == "id\tname\n"


class TestTsvRef:
    """tsv_ref() はネストした参照を id / name の 2 セルに展開する"""

    def test_expands_id_and_name(self):
        """`project: {id, name}` は (id, name) になる"""
        assert tsv_ref({"project": {"id": 3, "name": "redi"}}, "project") == (3, "redi")

    def test_missing_ref_is_two_empty_cells(self):
        """参照が無い (担当者未割り当てなど) ときも列数を崩さず 2 つとも None にする"""
        assert tsv_ref({"id": 1}, "assigned_to") == (None, None)
