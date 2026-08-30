"""エラーメッセージの出力先を守るテスト。"""

from redi.output import eprint


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
