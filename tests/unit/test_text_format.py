from typing import cast

from redi.api.issue import Issue
from redi.i18n import messages
from redi.text_format import issue_meta_rows, render_meta_table


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


class TestIssueMetaRows:
    """イシューのメタ情報 (CLI の issue view と TUI のプレビューで共有)"""

    def test_shows_parent_issue_id(self):
        """親チケットがあるときは `#<id>` として親の行に出す"""
        issue = cast(Issue, {"id": 2, "parent": {"id": 1}})
        assert (messages.meta_parent, "#1") in issue_meta_rows(issue)

    def test_keeps_parent_row_without_parent(self):
        """親チケットが無くても行は消さず、空値 (テーブル上は `-`) にする"""
        issue = cast(Issue, {"id": 2})
        assert (messages.meta_parent, "") in issue_meta_rows(issue)
