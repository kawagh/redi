"""カスタムクエリ操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とレスポンスの解釈は `api.query` が持つ。
"""

from __future__ import annotations

from redi.api import query as query_api
from redi.api.query import Query


def list_queries() -> list[Query]:
    """参照できるカスタムクエリを全件取得する。"""
    return query_api.fetch_queries()


def list_queries_for_project(project_id: str | None) -> list[Query]:
    """指定プロジェクトで使えるクエリ (プロジェクト固有 + グローバル) を返す。

    Redmine のクエリは `project_id` を持つプロジェクト固有のものと、持たない
    グローバルなものが混ざる。他プロジェクトのクエリを渡しても絞り込めないので
    選択肢から外す。`project_id` が None ならグローバルのみを返す。
    """
    queries = []
    for query in list_queries():
        owner = query.get("project_id")
        if owner is None or (project_id is not None and str(owner) == str(project_id)):
            queries.append(query)
    return queries
