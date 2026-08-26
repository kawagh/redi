import pytest
import requests

from redi.api.exceptions import RedmineConnectionException
from redi.cli import connection
from redi.client import RedmineClient
from redi.i18n.en import En


@pytest.fixture
def api_client() -> RedmineClient:
    return RedmineClient("https://redmine.example.com", "key")


class TestVerifyConnectionSuccess:
    """疎通できたときは user を返す"""

    def test_returns_user(self, api_client, monkeypatch):
        """成功時は ok=True で user が入り error は None"""
        monkeypatch.setattr(
            connection, "fetch_my_account", lambda *_, **__: {"login": "kawagh"}
        )

        result = connection.verify_connection(api_client, En())

        assert result.ok is True
        assert result.user == {"login": "kawagh"}
        assert result.error is None

    def test_passes_timeout(self, api_client, monkeypatch):
        """応答が返らない接続先に待たされ続けないよう timeout を渡す"""
        captured: dict = {}

        def fake_fetch(client, timeout=None):
            captured["timeout"] = timeout
            return {"login": "kawagh"}

        monkeypatch.setattr(connection, "fetch_my_account", fake_fetch)

        connection.verify_connection(api_client, En())

        assert captured["timeout"] == connection.VERIFY_TIMEOUT_SECONDS


class TestVerifyConnectionFailure:
    """疎通できないときは表示せず error に理由を入れて返す"""

    def _raise(self, monkeypatch, error: Exception) -> None:
        def fake_fetch(*_, **__):
            raise error

        monkeypatch.setattr(connection, "fetch_my_account", fake_fetch)

    def test_http_error(self, api_client, monkeypatch, capsys):
        """HTTPError はステータスと reason を含む文言になる"""
        response = requests.Response()
        response.status_code = 401
        response.reason = "Unauthorized"
        self._raise(monkeypatch, requests.exceptions.HTTPError(response=response))

        result = connection.verify_connection(api_client, En())

        assert result.ok is False
        assert result.user is None
        assert result.error is not None
        assert "401" in result.error
        assert "Unauthorized" in result.error
        # 表示は呼び出し側に任せるのでここでは出力しない
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_http_error_without_response(self, api_client, monkeypatch):
        """response を持たない HTTPError でも文言を組み立てられる"""
        self._raise(monkeypatch, requests.exceptions.HTTPError("boom"))

        result = connection.verify_connection(api_client, En())

        assert result.ok is False
        assert result.error is not None
        assert "boom" in result.error

    def test_connection_error(self, api_client, monkeypatch):
        """接続そのものが失敗した場合も error に理由が入る"""
        self._raise(monkeypatch, RedmineConnectionException("https://unreachable"))

        result = connection.verify_connection(api_client, En())

        assert result.ok is False
        assert result.error is not None
        assert "https://unreachable" in result.error
