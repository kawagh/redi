"""カスタムクエリ取得 API の単体テスト。"""

import requests

from redi.api import query as query_module


def _response(payload: dict) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response._content = requests.models.complexjson.dumps(payload).encode()
    return response


class TestFetchQueries:
    """fetch_queries は Redmine のページングを辿って全件返す"""

    def test_follows_pagination_until_total_count(self, monkeypatch):
        """total_count に届くまで offset を進めて全件集める"""
        pages = [
            {
                "queries": [{"id": i} for i in range(1, 101)],
                "total_count": 150,
            },
            {
                "queries": [{"id": i} for i in range(101, 151)],
                "total_count": 150,
            },
        ]
        calls: list[dict] = []

        def fake_get(_path, params=None):
            calls.append(params or {})
            return _response(pages[len(calls) - 1])

        monkeypatch.setattr(query_module.client, "get", fake_get)

        queries = query_module.fetch_queries()

        assert [q["id"] for q in queries] == list(range(1, 151))
        assert [c["offset"] for c in calls] == [0, 100]
