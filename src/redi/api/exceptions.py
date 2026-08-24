from typing import Literal, Self

import requests

ValidationAction = Literal["create", "update"]


def print_http_error_body(e: requests.exceptions.HTTPError) -> None:
    if e.response is not None:
        print(e.response.text)


class ProjectNotFoundException(Exception):
    """対象のプロジェクトが存在しないときに送出する例外。

    プロジェクトを指定した API が HTTP 404 を返した場合のほか、identifier や
    名前からの解決に失敗した場合にも送出する。

    `project_id` は呼び出し時に指定された値。
    """

    def __init__(self, project_id: str | None) -> None:
        super().__init__(str(project_id))
        self.project_id = project_id


class QueryNotFoundException(Exception):
    """指定したカスタムクエリが存在しない (または閲覧できない) ときに送出する例外。

    `query_id` は呼び出し時に指定された値。
    """

    def __init__(self, query_id: str) -> None:
        super().__init__(str(query_id))
        self.query_id = query_id


class IssueListNotFoundException(Exception):
    """イシュー一覧が 404 になったが、原因を特定できないときに送出する例外。

    Redmine は存在しない (または閲覧できない) プロジェクト・カスタムクエリの
    どちらでも 404 を返し、レスポンス本文にも区別が無い。両方を指定している場合は
    どちらが原因か判別できないため、api 層では断定せずにこの例外を送出し、
    切り分けは service 層に任せる。

    `project_id` / `query_id` は呼び出し時に指定された値。
    """

    def __init__(self, project_id: str, query_id: str) -> None:
        super().__init__(f"project_id={project_id} query_id={query_id}")
        self.project_id = project_id
        self.query_id = query_id


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
