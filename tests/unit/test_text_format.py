from redi.text_format import render_meta_table


class TestRenderMetaTable:
    """`[ラベル] 値` 形式のメタ情報テーブル (CLI の issue view と TUI のプレビューで共有)"""

    def test_aligns_label_column_by_display_width(self):
        """ラベル列は全角文字の表示幅込みで最大幅に揃える"""
        assert render_meta_table([("ステータス", "終了"), ("期日", "2026-04-01")]) == [
            "[ステータス] 終了",
            "[期日      ] 2026-04-01",
        ]

    def test_shows_placeholder_for_empty_value(self):
        """値が空のときは行を消さずに `-` を出す"""
        assert render_meta_table([("担当者", "")]) == ["[担当者] -"]
