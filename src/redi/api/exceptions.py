from typing import Literal, Self

import requests

ValidationAction = Literal["create", "update"]


def print_http_error_body(e: requests.exceptions.HTTPError) -> None:
    if e.response is not None:
        print(e.response.text)


class RedmineConnectionException(requests.exceptions.ConnectionError):
    """Redmine へ接続できなかったときに送出する例外。

    サーバ未起動やポート閉塞では TCP 接続自体が確立できず、requests が
    `ConnectionError` / `Timeout` を送出する。そのまま伝播させると 100 行前後の
    トレースバックになり、内部のファイルパスまで露出するため、接続先だけを
    持たせて呼び出し元が 1 行のメッセージを出せるようにする。

    `requests.exceptions.ConnectionError` を継承しているのは、通信失敗を
    画面内のメッセージに変えている TUI の `except requests.exceptions.RequestException`
    をそのまま活かすため。TUI は接続できなくてもアプリごと落ちずにエラー表示に
    留めたいので、CLI のトップレベルまで投げ上げたくない。
    `str(e)` が URL だけになるぶん、その表示も短くなる。

    `base_url` は接続を試みた Redmine の URL。
    """

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url)
        self.base_url = base_url


class ProjectNotFoundException(Exception):
    """対象のプロジェクトが存在しないときに送出する例外。

    プロジェクトを指定した API が HTTP 404 を返した場合のほか、identifier や
    名前からの解決に失敗した場合にも送出する。

    `project_id` は呼び出し時に指定された値。
    """

    def __init__(self, project_id: str | None) -> None:
        super().__init__(str(project_id))
        self.project_id = project_id


class ProjectPermissionDeniedException(Exception):
    """対象のプロジェクトを参照する権限が無いときに送出する例外 (HTTP 403)。

    Redmine はアーカイブ済みプロジェクトへの API アクセスにも 403 を返すため、
    アーカイブ済みと権限不足はこの例外では区別しない。

    `project_id` は呼び出し時に指定された値。
    """

    def __init__(self, project_id: str | None) -> None:
        super().__init__(str(project_id))
        self.project_id = project_id


class RedmineValidationException(Exception):
    """Redmine API がバリデーションエラー (HTTP 422) を返したときに送出する例外。

    - `errors` には Redmine がレスポンス JSON の `errors` 配列で返したメッセージを格納する
    - `resource` 例: "time_entry" / "wiki"
    - `action` は API 呼び出し時の意図 ("create" or "update")
    - JSON 解析に仮に失敗した場合は生のレスポンス本文を 1 要素として保持する
    """

    def __init__(
        self, resource: str, action: ValidationAction, errors: list[str]
    ) -> None:
        super().__init__("; ".join(errors) if errors else "validation error")
        self.resource = resource
        self.action: ValidationAction = action
        self.errors = errors

    @classmethod
    def from_response(
        cls,
        resource: str,
        action: ValidationAction,
        response: requests.Response,
    ) -> Self:
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
        return cls(resource, action, errors)
