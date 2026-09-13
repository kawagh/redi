import logging

import requests

from redi import config
from redi.api.exceptions import RedmineConnectionException

logger = logging.getLogger(__name__)


class RedmineClient:
    """Redmine REST API の薄いラッパ。

    各モジュールがシングルトンを束縛済みなので、実行中にプロファイルを切り替える
    ときは差し替えではなく `reconfigure()` で接続先を書き換える。
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        # パスと繋いだときに二重にならないよう、末尾のスラッシュはここで落とす
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["X-Redmine-API-Key"] = api_key

    def reconfigure(self, base_url: str, api_key: str) -> None:
        """接続先を差し替える。前の接続先の Cookie は持ち越さない。"""
        self.base_url = base_url.rstrip("/")
        self.session.headers["X-Redmine-API-Key"] = api_key
        self.session.cookies.clear()

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        """すべてのリクエストが通る唯一の経路。

        接続自体ができないケースはどのコマンドでも起きるので、
        個々の api モジュールではなくここで redi の例外に変換する。
        """
        url = self.base_url + path
        logger.debug("%s %s", method, url)
        try:
            response = getattr(self.session, method)(url, **kwargs)
        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as e:
            raise RedmineConnectionException(self.base_url) from e
        logger.debug("%s %s", response.status_code, response.reason)
        return response

    def get(self, path: str, **kwargs) -> requests.Response:
        return self._request("get", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self._request("post", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self._request("put", path, **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        return self._request("patch", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self._request("delete", path, **kwargs)


client = RedmineClient(config.redmine_url, config.redmine_api_key)

# 接続確認の待ち時間。応答が返らない URL に、対話入力や TUI が長く止められないため。
CONNECTION_CHECK_TIMEOUT_SECONDS = 10
