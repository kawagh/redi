from types import SimpleNamespace

import pytest

from redi import config
from redi.service import news_service


@pytest.fixture
def stub_news_api(monkeypatch):
    """作成 POST を `created` に、一覧取得の引数を `list_calls` に記録する。

    一覧は作成日時の降順で返る前提で `news_list` の先頭を最新として扱う。
    ニュースが Redmine に正しく届くかは CLI の E2E で見る。
    """

    state = SimpleNamespace(created=[], list_calls=[], news_list=[{"id": 7}])

    def fake_create_news(project_id, title, description, summary=None):
        state.created.append((project_id, title, description, summary))

    def fake_fetch_news_list(project_id=None, limit=None):
        state.list_calls.append((project_id, limit))
        return state.news_list

    monkeypatch.setattr(news_service.news_api, "create_news", fake_create_news)
    monkeypatch.setattr(news_service.news_api, "fetch_news_list", fake_fetch_news_list)
    monkeypatch.setattr(config, "redmine_url", "http://localhost:3001")
    return state


class TestCreateNews:
    """create_news が返す作成したニュースの URL"""

    def test_returns_url_of_latest_news(self, stub_news_api):
        """作成 API は id を返さないので、作成後に一覧の先頭を引いた id で URL を組み立てる"""
        url = news_service.create_news("demo", "タイトル", "本文", summary="概要")

        assert url == "http://localhost:3001/news/7"
        assert stub_news_api.created == [("demo", "タイトル", "本文", "概要")]
        # id の引き直しは作成したプロジェクトの最新 1 件だけを見る
        assert stub_news_api.list_calls == [("demo", 1)]


class TestNewsUrl:
    """news_url が組み立てる URL"""

    def test_build_url(self, stub_news_api):
        assert news_service.news_url(7) == "http://localhost:3001/news/7"
