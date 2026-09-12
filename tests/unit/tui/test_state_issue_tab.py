from redi.tui.state.issue_tab import IssueFilter


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
