import pytest

from redi.service import search_service


@pytest.fixture
def stub_search_api(monkeypatch) -> dict:
    """検索と引き直しの呼び出しを捕捉し、返す内容をテストから差し替える"""
    calls: dict = {
        "search_kwargs": None,
        "fetch_kwargs": None,
        "fetch_called": 0,
        # テストが上書きする戻り値
        "search_response": {"results": [], "total_count": 0},
        "fetched_issues": [],
    }

    def fake_search(**kwargs):
        calls["search_kwargs"] = kwargs
        return calls["search_response"]

    def fake_fetch_issues_page(**kwargs):
        calls["fetch_kwargs"] = kwargs
        calls["fetch_called"] += 1
        return {"issues": calls["fetched_issues"], "total_count": 999}

    monkeypatch.setattr(search_service, "search", fake_search)
    monkeypatch.setattr(search_service, "fetch_issues_page", fake_fetch_issues_page)
    return calls


def _results(*issue_ids: int) -> list[dict]:
    return [{"id": i, "type": "issue"} for i in issue_ids]


class TestSearchIssuesPage:
    """search_issues_page は検索結果を通常のイシュー一覧と同じ形に揃える"""

    def test_keeps_search_order(self, stub_search_api):
        """並びは検索 API が返した順を保つ (引き直しの id 降順に引きずられない)"""
        stub_search_api["search_response"] = {
            "results": _results(3, 1, 2),
            "total_count": 3,
        }
        stub_search_api["fetched_issues"] = [
            {"id": 3, "subject": "c"},
            {"id": 2, "subject": "b"},
            {"id": 1, "subject": "a"},
        ]

        page = search_service.search_issues_page("hooks")

        assert [issue["id"] for issue in page["issues"]] == [3, 1, 2]

    def test_total_count_comes_from_search(self, stub_search_api):
        """total_count は検索側の総数で、引き直したページの件数ではない"""
        stub_search_api["search_response"] = {
            "results": _results(1, 2),
            "total_count": 59,
        }
        stub_search_api["fetched_issues"] = [{"id": 1}, {"id": 2}]

        page = search_service.search_issues_page("hooks", limit=2, offset=0)

        assert page["total_count"] == 59

    def test_keeps_closed_issues(self, stub_search_api):
        """終了済みは type が issue-closed で返るが、イシューとして扱う"""
        stub_search_api["search_response"] = {
            "results": [
                {"id": 1, "type": "issue"},
                {"id": 2, "type": "issue-closed"},
            ],
            "total_count": 2,
        }
        stub_search_api["fetched_issues"] = [{"id": 1}, {"id": 2}]

        page = search_service.search_issues_page("hooks")

        assert [issue["id"] for issue in page["issues"]] == [1, 2]

    def test_drops_non_issue_results(self, stub_search_api):
        """イシュー以外の種別が混ざっても引き直しの対象にしない"""
        stub_search_api["search_response"] = {
            "results": [
                {"id": 1, "type": "issue"},
                {"id": 9, "type": "wiki-page"},
            ],
            "total_count": 2,
        }
        stub_search_api["fetched_issues"] = [{"id": 1}]

        search_service.search_issues_page("hooks")

        assert stub_search_api["fetch_kwargs"]["issue_id"] == "1"

    def test_refetch_includes_closed_issues(self, stub_search_api):
        """引き直しは status_id=* を渡す (既定では終了済みが落ちてしまうため)"""
        stub_search_api["search_response"] = {
            "results": _results(1),
            "total_count": 1,
        }
        stub_search_api["fetched_issues"] = [{"id": 1}]

        search_service.search_issues_page("hooks")

        assert stub_search_api["fetch_kwargs"]["status_id"] == "*"

    def test_refetch_limit_covers_all_ids(self, stub_search_api):
        """引き直しの limit は id の個数 (既定の 25 件で後半が切られないように)"""
        issue_ids = list(range(1, 31))
        stub_search_api["search_response"] = {
            "results": _results(*issue_ids),
            "total_count": 30,
        }
        stub_search_api["fetched_issues"] = [{"id": i} for i in issue_ids]

        search_service.search_issues_page("hooks", limit=30)

        assert stub_search_api["fetch_kwargs"]["limit"] == 30
        assert stub_search_api["fetch_kwargs"]["issue_id"] == ",".join(
            str(i) for i in issue_ids
        )

    def test_searches_only_issues_in_project(self, stub_search_api):
        """検索はイシューだけを対象にし、指定されたプロジェクトに絞る"""
        search_service.search_issues_page("hooks", project_id="redi", offset=20)

        assert stub_search_api["search_kwargs"]["types"] == ["issues"]
        assert stub_search_api["search_kwargs"]["project_id"] == "redi"
        assert stub_search_api["search_kwargs"]["offset"] == 20

    def test_skips_refetch_when_no_hit(self, stub_search_api):
        """ヒット0件なら引き直しの API を呼ばない"""
        stub_search_api["search_response"] = {"results": [], "total_count": 0}

        page = search_service.search_issues_page("no-such-word")

        assert page["issues"] == []
        assert page["total_count"] == 0
        assert stub_search_api["fetch_called"] == 0

    def test_drops_ids_that_cannot_be_fetched(self, stub_search_api):
        """引き直しで得られなかった id は落とす (検索後に削除された場合など)"""
        stub_search_api["search_response"] = {
            "results": _results(1, 2),
            "total_count": 2,
        }
        stub_search_api["fetched_issues"] = [{"id": 1}]

        page = search_service.search_issues_page("hooks")

        assert [issue["id"] for issue in page["issues"]] == [1]
