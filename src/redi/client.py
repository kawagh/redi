import logging

import requests

from redi.config import redmine_api_key, redmine_url

logger = logging.getLogger(__name__)


class RedmineClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers["X-Redmine-API-Key"] = api_key

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


client = RedmineClient(redmine_url or "", redmine_api_key or "")
