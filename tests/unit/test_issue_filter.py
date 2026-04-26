from redi.tui import issue_tab
from redi.tui.state import IssueFilter, TuiState


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


class TestFetchIssuesWithFilter:
    """fetch_issues_with_filter()はTuiStateのfilterをfetch_issuesに渡す"""

    def test_passes_filter_values_to_api(self, monkeypatch):
        """state.issue_tab.filter の値が fetch_issues の引数に反映される"""
        captured: dict = {}

        def fake_fetch(**kwargs):
            captured.update(kwargs)
            return []

        monkeypatch.setattr(issue_tab, "fetch_issues", fake_fetch)
        monkeypatch.setattr(issue_tab, "default_project_id", "demo")

        state = TuiState()
        state.page_size = 20
        state.issue_tab.filter = IssueFilter(
            status_id="closed",
            status_label="closed のみ",
            assigned_to_id="me",
            assigned_to_label="自分",
        )
        issue_tab.fetch_issues_with_filter(state, offset=40)

        assert captured == {
            "project_id": "demo",
            "status_id": "closed",
            "assigned_to": "me",
            "limit": 20,
            "offset": 40,
        }

    def test_passes_none_when_filter_unset(self, monkeypatch):
        """フィルタ未設定なら status_id / assigned_to も None で渡す"""
        captured: dict = {}

        def fake_fetch(**kwargs):
            captured.update(kwargs)
            return []

        monkeypatch.setattr(issue_tab, "fetch_issues", fake_fetch)
        monkeypatch.setattr(issue_tab, "default_project_id", "demo")

        state = TuiState()
        state.page_size = 10
        issue_tab.fetch_issues_with_filter(state, offset=0)

        assert captured["status_id"] is None
        assert captured["assigned_to"] is None


class TestReloadWithFilter:
    """reload_with_filter()はoffset/cursorをリセットしてフィルタで再取得する"""

    def test_resets_offset_cursor_and_fetches(self, monkeypatch):
        """offset=0 で再取得し、cursor も 0 に戻す"""
        monkeypatch.setattr(
            issue_tab,
            "fetch_issues",
            lambda **kwargs: [{"id": 1, "subject": "filtered"}],
        )
        monkeypatch.setattr(issue_tab, "default_project_id", "demo")

        state = TuiState()
        state.page_size = 20
        state.issue_tab.offset = 100
        state.issue_tab.cursor = 5
        state.issue_tab.filter = IssueFilter(
            status_id="closed", status_label="closed のみ"
        )

        issue_tab.reload_with_filter(state)

        assert state.issue_tab.offset == 0
        assert state.issue_tab.cursor == 0
        assert state.issue_tab.issues == [{"id": 1, "subject": "filtered"}]
