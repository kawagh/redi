import pytest
import requests

from redi.api import user as user_module
from redi.api.user import USERS_PAGE_LIMIT, UserPermissionDeniedException


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self)

    def json(self) -> dict:
        return self._payload


def _users(start: int, count: int) -> list[dict]:
    return [{"id": i, "login": f"user{i}"} for i in range(start, start + count)]


@pytest.fixture
def captured_params(monkeypatch) -> list[dict]:
    """fetch_users が client.get に渡した params を呼び出し順に記録する"""
    captured: list[dict] = []

    def fake_get(path: str, **kwargs) -> FakeResponse:
        captured.append(kwargs["params"])
        return FakeResponse({"users": [], "total_count": 0})

    monkeypatch.setattr(user_module.client, "get", fake_get)
    return captured


class TestFetchUsersPaging:
    """fetch_users は all_pages を指定したときだけ、既定の件数で打ち切らず全件返す"""

    def test_default_sends_no_paging_params(self, captured_params):
        """既定ではページングを足さず、Redmine の既定件数に任せて1回だけ呼ぶ"""
        user_module.fetch_users()

        assert captured_params == [{}]

    def test_sends_paging_params(self, captured_params):
        """all_pages では既定の件数で切られないようページングを指定する"""
        user_module.fetch_users(all_pages=True)

        assert captured_params == [{"limit": USERS_PAGE_LIMIT, "offset": 0}]

    def test_follows_total_count(self, monkeypatch):
        """total_count に届くまで offset を進めて全件返す"""
        pages = [
            FakeResponse({"users": _users(1, USERS_PAGE_LIMIT), "total_count": 150}),
            FakeResponse({"users": _users(101, 50), "total_count": 150}),
        ]
        offsets: list[int] = []

        def fake_get(path: str, **kwargs) -> FakeResponse:
            offsets.append(kwargs["params"]["offset"])
            return pages[len(offsets) - 1]

        monkeypatch.setattr(user_module.client, "get", fake_get)

        users = user_module.fetch_users(all_pages=True)

        assert offsets == [0, USERS_PAGE_LIMIT]
        assert len(users) == 150


class TestFetchUsersExplicitPaging:
    """limit / offset はそのまま Redmine に渡す"""

    @pytest.mark.parametrize(
        ("kwargs", "expected"),
        [
            ({"limit": 5}, {"limit": 5}),
            ({"offset": 10}, {"offset": 10}),
            ({"limit": 5, "offset": 10}, {"limit": 5, "offset": 10}),
        ],
        ids=["limit", "offset", "both"],
    )
    def test_takes_one_page(self, monkeypatch, kwargs, expected):
        """指定された分だけを送り、total_count が残っていても追わない"""
        calls: list[dict] = []

        def fake_get(path: str, **get_kwargs) -> FakeResponse:
            calls.append(get_kwargs["params"])
            return FakeResponse({"users": _users(1, 5), "total_count": 150})

        monkeypatch.setattr(user_module.client, "get", fake_get)

        users = user_module.fetch_users(**kwargs)

        assert calls == [expected]
        assert len(users) == 5


class TestFetchUsersPermission:
    """一覧は管理者権限が要る"""

    def test_permission_denied(self, monkeypatch):
        """403 は UserPermissionDeniedException に変換して HTTP を呼び出し元に見せない"""

        def fake_get(path: str, **kwargs) -> FakeResponse:
            return FakeResponse({}, status_code=403)

        monkeypatch.setattr(user_module.client, "get", fake_get)

        with pytest.raises(UserPermissionDeniedException):
            user_module.fetch_users()
