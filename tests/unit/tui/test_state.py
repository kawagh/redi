from redi.i18n import messages
from redi.tui.state import IssueFilter, TimeEntryFilter


class TestIssueFilter:
    """IssueFilter は Issue 一覧のサーバーサイドフィルタ条件を保持する"""

    class TestIsActive:
        """is_active()はフィルタが何か設定されているかを返す"""

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

    class TestShortLabel:
        """short_label()はステータスバー表示用のラベルを返す"""

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


class TestTimeEntryFilter:
    """TimeEntryFilter は time_entry 一覧のユーザーフィルタ条件を保持する"""

    def test_default_filters_by_me(self):
        """デフォルトでは「自分」(me) でフィルタする"""
        f = TimeEntryFilter()
        assert f.user_id == "me"
        assert f.is_active() is True
        # short_label のラベル部は messages から取得するので言語に依存する
        assert f.short_label() == f"user={messages.tui_filter_assignee_me}"

    def test_unset_is_inactive(self):
        """user_id を None にすればフィルタは非アクティブ"""
        f = TimeEntryFilter(user_id=None, user_label="")
        assert f.is_active() is False
        assert f.short_label() == ""

    def test_specific_user(self):
        """特定のユーザーIDを指定したときのラベル"""
        f = TimeEntryFilter(user_id="42", user_label="Alice")
        assert f.is_active() is True
        assert f.short_label() == "user=Alice"
