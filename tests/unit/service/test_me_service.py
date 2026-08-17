import pytest
import requests

from redi.service import me_service


@pytest.fixture
def stub_me_api(monkeypatch):
    """`fetch_my_account` の戻りを差し替える。

    HTTP が正しく呼べているかは E2E (`tests/e2e/test_me_cli.py`) で見る。
    """

    def set_account(account):
        monkeypatch.setattr(me_service.me_api, "fetch_my_account", lambda: account)

    def set_error(error):
        def raise_error():
            raise error

        monkeypatch.setattr(me_service.me_api, "fetch_my_account", raise_error)

    return set_account, set_error


class TestReadMyAccount:
    """read_my_account が返すアカウント"""

    def test_drops_api_key(self, stub_me_api):
        """api_key は漏らしたくないので落として返す"""
        set_account, _ = stub_me_api
        set_account({"id": 1, "login": "admin", "api_key": "secret"})

        account = me_service.read_my_account()

        assert account == {"id": 1, "login": "admin"}


class TestReadMyUserId:
    """read_my_user_id が返すユーザー id"""

    def test_returns_id_as_str(self, stub_me_api):
        """TUI が author id と文字列で突き合わせられるよう str で返す"""
        set_account, _ = stub_me_api
        set_account({"id": 5, "login": "admin"})

        assert me_service.read_my_user_id() == "5"

    def test_returns_none_on_request_error(self, stub_me_api):
        """取得に失敗しても TUI の起動を止めないため None を返す"""
        _, set_error = stub_me_api
        set_error(requests.ConnectionError())

        assert me_service.read_my_user_id() is None
