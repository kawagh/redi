from redi.text_format import display_width, pad_display, truncate_display


class TestDisplayWidth:
    """表示幅は全角を 2 幅として数える"""

    def test_counts_fullwidth_as_two(self):
        """全角文字は 2 幅、半角文字は 1 幅"""
        assert display_width("あa") == 3


class TestPadDisplay:
    """pad_display は表示幅で右詰めする"""

    def test_pads_to_display_width(self):
        """全角込みで指定幅になるまで空白を足す"""
        assert display_width(pad_display("あa", 8)) == 8

    def test_keeps_text_longer_than_width(self):
        """指定幅を超えるテキストは削らない"""
        assert pad_display("あああ", 2) == "あああ"


class TestTruncateDisplay:
    """truncate_display は表示幅で切り詰める"""

    def test_keeps_text_within_width(self):
        """収まるテキストはそのまま返す"""
        assert truncate_display("あいう", 6) == "あいう"

    def test_truncates_with_ellipsis(self):
        """はみ出す分は … に置き換え、指定幅を超えない"""
        truncated = truncate_display("あいうえお", 6)

        assert truncated.endswith("…")
        assert display_width(truncated) <= 6

    def test_does_not_split_fullwidth_char(self):
        """全角文字の途中で切って幅が溢れることはない"""
        assert display_width(truncate_display("あいうえお", 5)) <= 5
