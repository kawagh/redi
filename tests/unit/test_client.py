import pytest
import requests

from redi.api.exceptions import RedmineConnectionException
from redi.client import RedmineClient


class TestReconfigure:
    """reconfigure() は接続先を in-place で書き換える"""

    def test_switches_base_url_and_api_key(self):
        """各モジュールが束縛済みのシングルトンを差し替えずに切り替えられる"""
        client = RedmineClient("https://main.example.com", "key-main")

        client.reconfigure("https://sub.example.com", "key-sub")

        assert client.base_url == "https://sub.example.com"
        assert client.session.headers["X-Redmine-API-Key"] == "key-sub"

    def test_clears_cookies(self):
        """前の接続先のセッション Cookie を持ち越さない"""
        client = RedmineClient("https://main.example.com", "key-main")
        client.session.cookies.set("_redmine_session", "old")

        client.reconfigure("https://sub.example.com", "key-sub")

        assert len(client.session.cookies) == 0


class TestConnectionError:
    """接続できないときは redi の例外に変換する

    そのまま requests の例外を通すと呼び出し元まで 100 行前後のトレースバックが
    伝わるため、全リクエストの通り道である `_request` で変換する。
    """

    @pytest.fixture
    def client(self) -> RedmineClient:
        return RedmineClient("http://localhost:3000", "key")

    def _raise(self, exception: Exception):
        def _send(url, **kwargs):
            raise exception

        return _send

    @pytest.mark.parametrize(
        "exception",
        [
            requests.exceptions.ConnectionError("refused"),
            requests.exceptions.Timeout("timed out"),
        ],
        ids=["connection_error", "timeout"],
    )
    def test_converts_to_redmine_connection_exception(
        self, client, monkeypatch, exception
    ):
        """接続失敗とタイムアウトは RedmineConnectionException にする"""
        monkeypatch.setattr(client.session, "get", self._raise(exception))

        with pytest.raises(RedmineConnectionException) as e:
            client.get("/projects.json")

        assert e.value.base_url == "http://localhost:3000"

    def test_message_is_the_url_only(self, client, monkeypatch):
        """表示に使う str() は接続先だけにして、生のトレースバック文字列を持ち込まない"""
        monkeypatch.setattr(
            client.session,
            "get",
            self._raise(requests.exceptions.ConnectionError("very long urllib3 text")),
        )

        with pytest.raises(RedmineConnectionException) as e:
            client.get("/projects.json")

        assert str(e.value) == "http://localhost:3000"

    def test_is_a_requests_connection_error(self, client, monkeypatch):
        """通信失敗を画面内に留める TUI の except RequestException を素通りさせない"""
        monkeypatch.setattr(
            client.session,
            "get",
            self._raise(requests.exceptions.ConnectionError("refused")),
        )

        with pytest.raises(requests.exceptions.RequestException):
            client.get("/projects.json")

    def test_http_error_status_is_not_converted(self, client, monkeypatch):
        """サーバが応答を返しているケース (404 等) はここでは扱わない"""
        response = requests.Response()
        response.status_code = 404
        monkeypatch.setattr(client.session, "get", lambda url, **kwargs: response)

        assert client.get("/projects.json").status_code == 404
