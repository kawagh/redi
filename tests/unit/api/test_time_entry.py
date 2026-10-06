import requests

from redi.api import time_entry as time_entry_module


def _issues_response(issue_ids: list[int]) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    issues = ",".join(f'{{"id": {i}, "subject": "s{i}"}}' for i in issue_ids)
    response._content = f'{{"issues": [{issues}]}}'.encode()
    return response


class TestFetchIssueSubjects:
    """fetch_issue_subjects は作業時間が参照するチケットの件名を漏れなく引く"""

    def test_includes_closed_issues(self, monkeypatch):
        """完了済みのチケットも件名を出せるよう、ステータスを問わず引く"""
        captured: list[dict] = []

        def fake_get(path, params):
            captured.append(params)
            return _issues_response([1])

        monkeypatch.setattr(time_entry_module.client, "get", fake_get)

        assert time_entry_module.fetch_issue_subjects([1]) == {1: "s1"}
        assert captured[0]["status_id"] == "*"

    def test_splits_many_ids(self, monkeypatch):
        """既定の上限で切れないよう、100 件ごとに分けて全件の件名を返す"""
        captured: list[list[int]] = []

        def fake_get(path, params):
            ids = [int(i) for i in params["issue_id"].split(",")]
            captured.append(ids)
            assert params["limit"] == len(ids)
            return _issues_response(ids)

        monkeypatch.setattr(time_entry_module.client, "get", fake_get)

        subjects = time_entry_module.fetch_issue_subjects(list(range(1, 151)))

        assert [len(ids) for ids in captured] == [100, 50]
        assert len(subjects) == 150

    def test_no_request_without_ids(self, monkeypatch):
        """引く id が無ければリクエストしない"""

        def fake_get(path, params):
            raise AssertionError("should not request")

        monkeypatch.setattr(time_entry_module.client, "get", fake_get)

        assert time_entry_module.fetch_issue_subjects([]) == {}
