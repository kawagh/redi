"""カスタムクエリ操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とレスポンスの解釈は `api.query` が持つ。
"""

from __future__ import annotations

from redi.api import query as query_api
from redi.api.exceptions import ProjectNotFoundException
from redi.api.query import Query
from redi.service.project_service import resolve_project_id


def list_queries() -> list[Query]:
    """参照できるカスタムクエリを全件取得する。"""
    return query_api.fetch_queries()


def list_queries_for_project(project_id: str | None) -> list[Query]:
    """指定プロジェクトで使えるクエリ (プロジェクト固有 + グローバル) を返す。

    Redmine のクエリは `project_id` を持つプロジェクト固有のものと、持たない
    グローバルなものが混ざる。他プロジェクトのクエリを渡しても絞り込めないので
    選択肢から外す。`project_id` が None ならグローバルのみを返す。

    クエリが持つ `project_id` は数値なので、identifier で指定されている場合は
    数値 id へ解決してから突き合わせる (config の `default_project_id` には
    identifier も書けるため、解決しないとプロジェクト固有のクエリを取りこぼす)。
    """
    owner_id = _resolve_owner_id(project_id)
    queries = []
    for query in list_queries():
        owner = query.get("project_id")
        if owner is None or (owner_id is not None and str(owner) == owner_id):
            queries.append(query)
    return queries


def _resolve_owner_id(project_id: str | None) -> str | None:
    """突き合わせに使う数値 project_id を返す。解決できなければ None。

    解決できないときにグローバルのクエリだけでも選べるよう、例外にはしない。
    """
    if project_id is None:
        return None
    try:
        return resolve_project_id(project_id)
    except ProjectNotFoundException:
        return None
