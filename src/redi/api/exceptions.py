import requests
from typing import Self


class RedmineValidationException(Exception):
    """Redmine API がバリデーションエラー (HTTP 422) を返したときに送出する例外。

    - `errors` には Redmine がレスポンス JSON の `errors` 配列で返したメッセージを格納する
    - `resource` 例: "time_entry"
    - JSON 解析に仮に失敗した場合は生のレスポンス本文を 1 要素として保持する
    """

    def __init__(self, resource: str, errors: list[str]) -> None:
        super().__init__("; ".join(errors) if errors else "validation error")
        self.resource = resource
        self.errors = errors

    @classmethod
    def from_response(cls, resource: str, response: requests.Response) -> Self:
        errors: list[str] = []
        try:
            body = response.json()
        except requests.exceptions.JSONDecodeError:
            body = None
        if isinstance(body, dict):
            raw = body.get("errors")
            if isinstance(raw, list):
                errors = [str(e) for e in raw]
        # 422 で想定している型でなかった場合
        if not errors:
            text = response.text.strip()
            if text:
                errors = [text]
        return cls(resource, errors)
