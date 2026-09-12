from redi import config
from redi.api import PAGE_LIMIT_MAX
from redi.i18n import messages
from redi.tui.state import (
    FIXED_ROWS,
    IssueFilter,
    IssueFind,
    TimeEntryFilter,
    TuiResult,
    TuiState,
    compute_page_size,
    realign_page,
)


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

        def test_tracker_set_is_active(self):
            """tracker_id だけ設定でもアクティブ"""
            f = IssueFilter(tracker_id="1", tracker_label="バグ")
            assert f.is_active() is True

        def test_query_set_is_active(self):
            """query_id だけ設定でもアクティブ"""
            f = IssueFilter(query_id="7", query_label="未完了")
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

        def test_tracker_only(self):
            """tracker のみ設定なら tracker= だけ返す"""
            f = IssueFilter(tracker_id="1", tracker_label="バグ")
            assert f.short_label() == "tracker=バグ"

        def test_all_fields(self):
            """全て設定なら status/assignee/tracker の順に空白区切りで返す"""
            f = IssueFilter(
                status_id="*",
                status_label="全て (open + closed)",
                assigned_to_id="me",
                assigned_to_label="自分",
                tracker_id="1",
                tracker_label="バグ",
            )
            assert (
                f.short_label()
                == "status=全て (open + closed) assignee=自分 tracker=バグ"
            )

        def test_query_only(self):
            """query が有効なら query= だけ返す"""
            f = IssueFilter(query_id="7", query_label="未完了")
            assert f.short_label() == "query=未完了"

    class TestApply:
        """apply() は選ばれた1項目を反映し、クエリとの排他を保つ"""

        def test_query_clears_other_conditions(self):
            """クエリを選ぶと status/assignee/tracker はクリアされる

            Redmine は query_id と同時に渡した条件を捨てるため、残すと
            ステータスバーの表示が実際の絞り込みと食い違う。
            """
            f = IssueFilter(
                status_id="*",
                status_label="全て",
                assigned_to_id="me",
                assigned_to_label="自分",
                tracker_id="1",
                tracker_label="バグ",
            )

            f.apply("query", "7", "未完了")

            assert f.query_id == "7"
            assert f.status_id is None
            assert f.assigned_to_id is None
            assert f.tracker_id is None

        def test_condition_clears_query(self):
            """status/assignee/tracker を選ぶとクエリはクリアされる"""
            f = IssueFilter(query_id="7", query_label="未完了")

            f.apply("tracker", "1", "バグ")

            assert f.tracker_id == "1"
            assert f.query_id is None

        def test_unspecified_does_not_clear_the_other_side(self):
            """(指定なし) の選択は絞り込みを外す操作なので反対側に触らない"""
            f = IssueFilter(query_id="7", query_label="未完了")

            f.apply("tracker", None, "(指定なし)")

            assert f.query_id == "7"
            assert f.tracker_id is None


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


class TestEffectiveProjectId:
    """effective_project_id() は override > config の優先順位で解決する"""

    def test_override_wins(self, monkeypatch):
        monkeypatch.setattr(config, "default_project_id", "5")
        monkeypatch.setattr(config, "wiki_project_id", "7")
        state = TuiState(project_id="2")

        assert state.effective_project_id() == "2"
        # 明示切替は wiki_project_id より優先する
        assert state.effective_wiki_project_id() == "2"

    def test_falls_back_to_config(self, monkeypatch):
        monkeypatch.setattr(config, "default_project_id", "5")
        monkeypatch.setattr(config, "wiki_project_id", "7")
        state = TuiState()

        assert state.effective_project_id() == "5"
        assert state.effective_wiki_project_id() == "7"

    def test_wiki_falls_back_to_default_project(self, monkeypatch):
        monkeypatch.setattr(config, "default_project_id", "5")
        monkeypatch.setattr(config, "wiki_project_id", None)
        state = TuiState()

        assert state.effective_wiki_project_id() == "5"

    def test_none_when_nothing_is_set(self, monkeypatch):
        monkeypatch.setattr(config, "default_project_id", None)
        monkeypatch.setattr(config, "wiki_project_id", None)
        state = TuiState()

        assert state.effective_project_id() is None
        assert state.effective_wiki_project_id() is None


class TestCarryOver:
    """carry_over() は action 実行後の次ループ用に TuiState を作り直す"""

    def test_issue_filter_is_preserved(self):
        """issue タブの絞り込み条件は次ループの TuiState に引き継がれる"""
        prev = TuiState()
        prev.issue_tab.filter = IssueFilter(
            status_id="closed", status_label="closed のみ"
        )
        result = TuiResult(action="comment", tab="issues", issue_id="1")

        next_state = prev.carry_over(result)

        assert next_state.issue_tab.filter == prev.issue_tab.filter
        assert next_state.issue_tab.filter.status_id == "closed"

    def test_issue_find_is_preserved(self):
        """F で掛けた検索も次ループの TuiState に引き継がれる"""
        prev = TuiState()
        prev.issue_tab.find = IssueFind(query="hooks")
        result = TuiResult(action="comment", tab="issues", issue_id="1")

        next_state = prev.carry_over(result)

        assert next_state.issue_tab.find.query == "hooks"

    def test_time_entry_filter_is_preserved(self):
        """time_entry タブの絞り込み条件も引き継がれる"""
        prev = TuiState()
        prev.time_entry_tab.filter = TimeEntryFilter(user_id="42", user_label="Alice")
        result = TuiResult(action="update", tab="time_entries", time_entry_id="9")

        next_state = prev.carry_over(result)

        assert next_state.time_entry_tab.filter == prev.time_entry_tab.filter
        assert next_state.time_entry_tab.filter.user_id == "42"

    def test_project_override_is_preserved(self):
        """p で切り替えたプロジェクトは action 実行後の次ループにも引き継がれる"""
        prev = TuiState(project_id="2", project_label="Beta")
        result = TuiResult(action="create", tab="issues", issue_id="")

        next_state = prev.carry_over(result)

        assert next_state.project_id == "2"
        assert next_state.project_label == "Beta"


class TestComputePageSize:
    """compute_page_size() は端末の行数から 1 ページの取得件数を決める"""

    def test_subtracts_fixed_rows(self):
        """タブバー・罫線・ステータスバーの固定行を引いた値が一覧に使える行数になる"""
        assert compute_page_size(30) == 30 - FIXED_ROWS

    def test_returns_at_least_one(self):
        """固定行しか入らない小さな端末でも 1 件は取得する"""
        assert compute_page_size(FIXED_ROWS) == 1
        assert compute_page_size(1) == 1

    def test_clamps_to_redmine_limit(self):
        """Redmine の limit 上限を超える行数では上限で頭打ちにする

        上限を超える limit を投げても実際には上限件数しか返らず、
        ステータスバーの Page 表示と実データがずれるため。
        """
        assert compute_page_size(PAGE_LIMIT_MAX + FIXED_ROWS + 50) == PAGE_LIMIT_MAX


class TestApplyTerminalRows:
    """apply_terminal_rows() は page_size を更新し、変化の有無を返す"""

    def test_updates_and_reports_change(self):
        """page_size が変わったら値を書き換えて True を返す"""
        state = TuiState()
        state.page_size = 10

        assert state.apply_terminal_rows(30 + FIXED_ROWS) is True
        assert state.page_size == 30

    def test_reports_no_change_when_same(self):
        """同じ行数なら page_size を据え置き False を返す"""
        state = TuiState()
        state.page_size = compute_page_size(30)

        assert state.apply_terminal_rows(30) is False
        assert state.page_size == compute_page_size(30)

    def test_reports_no_change_when_clamped_to_same_value(self):
        """行数が変わっても上限に丸められて同じ値になるなら False を返す"""
        state = TuiState()
        state.apply_terminal_rows(PAGE_LIMIT_MAX + FIXED_ROWS + 10)

        assert state.apply_terminal_rows(PAGE_LIMIT_MAX + FIXED_ROWS + 20) is False
        assert state.page_size == PAGE_LIMIT_MAX


class TestRealignPage:
    """realign_page() は選択行を保ったまま offset をページ境界へ揃える"""

    def test_keeps_selected_row_when_page_size_shrinks(self):
        """page_size が縮んでも選択行の絶対位置は変わらない"""
        offset, cursor = realign_page(offset=0, cursor=15, page_size=10)

        assert offset + cursor == 15
        assert (offset, cursor) == (10, 5)

    def test_keeps_selected_row_when_page_size_grows(self):
        """page_size が広がっても選択行の絶対位置は変わらない"""
        offset, cursor = realign_page(offset=20, cursor=3, page_size=40)

        assert offset + cursor == 23
        assert (offset, cursor) == (0, 23)

    def test_offset_is_multiple_of_page_size(self):
        """揃えた後の offset は必ず page_size の倍数になる (Page 表示がずれないため)"""
        for page_size in (3, 7, 25):
            offset, _cursor = realign_page(offset=13, cursor=4, page_size=page_size)
            assert offset % page_size == 0

    def test_first_page_stays_at_zero(self):
        """先頭ページ内の選択行は offset 0 のまま維持される"""
        assert realign_page(offset=0, cursor=2, page_size=10) == (0, 2)
