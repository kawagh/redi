from redi.i18n import messages
from redi.tui.state.time_entry_tab import TimeEntryFilter


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
