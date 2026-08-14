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
