import logging

import requests

from redi import config

logger = logging.getLogger(__name__)


class RedmineClient:
    """Redmine REST API の薄いラッパ。

    各モジュールがシングルトンを束縛済みなので、実行中にプロファイルを切り替える
    ときは差し替えではなく `reconfigure()` で接続先を書き換える。
    """

    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers["X-Redmine-API-Key"] = api_key

    def reconfigure(self, base_url: str, api_key: str) -> None:
        """接続先を差し替える。前の接続先の Cookie は持ち越さない。"""
        self.base_url = base_url
        self.session.headers["X-Redmine-API-Key"] = api_key
        self.session.cookies.clear()

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = self.base_url + path
        logger.debug("%s %s", method, url)
        response = getattr(self.session, method)(url, **kwargs)
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
