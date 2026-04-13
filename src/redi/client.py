import requests

from redi.config import redmine_api_key, redmine_url


class RedmineClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers["X-Redmine-API-Key"] = api_key

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(self.base_url + path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.session.post(self.base_url + path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.session.put(self.base_url + path, **kwargs)

    def patch(self, path: str, **kwargs) -> requests.Response:
        return self.session.patch(self.base_url + path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.session.delete(self.base_url + path, **kwargs)


client = RedmineClient(redmine_url or "", redmine_api_key or "")
