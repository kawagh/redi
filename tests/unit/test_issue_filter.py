from redi.tui.state import IssueFilter


class TestIssueFilterIsActive:
    """IssueFilter.is_active()はフィルタが何か設定されているかを返す"""

    def test_both_fields_unset_is_inactive(self):
        """status_id も assigned_to_id も None なら非アクティブ"""
        f = IssueFilter()
        assert f.is_active() is False

    def test_status_set_is_active(self):
        """status_id だけ設定でもアクティブ"""
        f = IssueFilter(status_id="closed", status_label="closed のみ")
        assert f.is_active() is True

    def test_assignee_set_is_active(self):
        """assigned_to_id だけ設定でもアクティブ"""
        f = IssueFilter(assigned_to_id="me", assigned_to_label="自分")
        assert f.is_active() is True


class TestIssueFilterShortLabel:
    """IssueFilter.short_label()はステータスバー表示用のラベルを返す"""

    def test_no_filter_returns_empty(self):
        """フィルタ未設定なら空文字を返す"""
        assert IssueFilter().short_label() == ""

    def test_status_only(self):
        """status のみ設定なら status= だけ返す"""
        f = IssueFilter(status_id="closed", status_label="closed のみ")
        assert f.short_label() == "status=closed のみ"

    def test_assignee_only(self):
        """assignee のみ設定なら assignee= だけ返す"""
        f = IssueFilter(assigned_to_id="me", assigned_to_label="自分")
        assert f.short_label() == "assignee=自分"

    def test_both_fields(self):
        """両方設定なら両方を空白区切りで返す"""
        f = IssueFilter(
            status_id="*",
            status_label="全て (open + closed)",
            assigned_to_id="me",
            assigned_to_label="自分",
        )
        assert f.short_label() == "status=全て (open + closed) assignee=自分"
