import pytest
import requests

from redi.service import wiki_service
from redi.service.wiki_service import WikiPageNotFoundError, delete_page


class _Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code}")


@pytest.fixture
def responds(monkeypatch):
    """DELETE の呼び出し先を記録し、指定したステータスコードを返すスタブ。"""

    def _responds(status_code: int) -> list[str]:
        paths: list[str] = []

        def fake_delete(path: str) -> _Response:
            paths.append(path)
            return _Response(status_code)

        monkeypatch.setattr(wiki_service.client, "delete", fake_delete)
        return paths

    return _responds


class TestDeletePage:
    """delete_page() は Wiki ページの削除要求を出し、応答を例外に翻訳する"""

    def test_requests_wiki_page_endpoint(self, responds):
        """project_id と page_title から Wiki ページの DELETE 先を組み立てる"""
        paths = responds(200)

        delete_page("myproject", "Home")

        assert paths == ["/projects/myproject/wiki/Home.json"]

    def test_raises_not_found_for_404(self, responds):
        """対象ページが無い (404) ときは WikiPageNotFoundError にする"""
        responds(404)

        with pytest.raises(WikiPageNotFoundError) as e:
            delete_page("myproject", "Missing")

        assert e.value.page_title == "Missing"

    def test_raises_http_error_for_other_status(self, responds):
        """404 以外の HTTP エラーは HTTPError のまま呼び出し元に渡す"""
        responds(403)

        with pytest.raises(requests.exceptions.HTTPError):
            delete_page("myproject", "Home")
