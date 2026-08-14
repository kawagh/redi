import pytest
import requests

from redi.api import account as account_module
from redi.i18n.en import En


class FakeResponse:
    def __init__(self, user: dict) -> None:
        self._user = user

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {"user": self._user}


@pytest.fixture
def captured_request(monkeypatch) -> dict:
    """verify_connection が requests.get に渡した引数を捕捉する"""
    captured: dict = {}

    def fake_get(url: str, **kwargs) -> FakeResponse:
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        captured["timeout"] = kwargs.get("timeout")
        return FakeResponse({"login": "kawagh"})

    monkeypatch.setattr(account_module.requests, "get", fake_get)
    return captured


class TestVerifyConnectionSuccess:
    """疎通できたときは user を返す"""

    def test_returns_user(self, captured_request):
        """成功時は ok=True で user が入り error は None"""
        result = account_module.verify_connection(
            "https://redmine.example.com", "key", En()
        )
        assert result.ok is True
        assert result.user == {"login": "kawagh"}
        assert result.error is None

    def test_requests_my_account(self, captured_request):
        """/my/account.json を API キー付きで叩く"""
        account_module.verify_connection("https://redmine.example.com", "key", En())
        assert captured_request["url"] == "https://redmine.example.com/my/account.json"
        assert captured_request["headers"] == {"X-Redmine-API-Key": "key"}

    def test_strips_trailing_slash(self, captured_request):
        """末尾スラッシュ付きの URL でもパスが二重にならない"""
        account_module.verify_connection("https://redmine.example.com/", "key", En())
        assert captured_request["url"] == "https://redmine.example.com/my/account.json"


class TestVerifyConnectionFailure:
    """疎通できないときは print せず error に理由を入れて返す"""

    def test_http_error(self, monkeypatch, capsys):
        """HTTPError はステータスと reason を含む文言になる"""
        response = requests.Response()
        response.status_code = 401
        response.reason = "Unauthorized"

        def fake_get(url: str, **kwargs):
            raise requests.exceptions.HTTPError(response=response)

        monkeypatch.setattr(account_module.requests, "get", fake_get)
        result = account_module.verify_connection(
            "https://redmine.example.com", "key", En()
        )
        assert result.ok is False
        assert result.user is None
        assert result.error is not None
        assert "401" in result.error
        assert "Unauthorized" in result.error
        # 表示は呼び出し側に任せるのでここでは出力しない
        assert capsys.readouterr().out == ""

    def test_http_error_without_response(self, monkeypatch):
        """response を持たない HTTPError でも文言を組み立てられる"""

        def fake_get(url: str, **kwargs):
            raise requests.exceptions.HTTPError("boom")

        monkeypatch.setattr(account_module.requests, "get", fake_get)
        result = account_module.verify_connection(
            "https://redmine.example.com", "key", En()
        )
        assert result.ok is False
        assert result.error is not None
        assert "boom" in result.error

    def test_connection_error(self, monkeypatch):
        """接続そのものが失敗した場合も error に理由が入る"""

        def fake_get(url: str, **kwargs):
            raise requests.exceptions.ConnectionError("unreachable")

        monkeypatch.setattr(account_module.requests, "get", fake_get)
        result = account_module.verify_connection(
            "https://redmine.example.com", "key", En()
        )
        assert result.ok is False
        assert result.error is not None
        assert "unreachable" in result.error
