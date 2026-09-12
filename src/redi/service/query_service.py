"""カスタムクエリ操作のサービス層。

CLI と TUI で共通の手順をここに置く。HTTP とレスポンスの解釈は `api.query` が持つ。
"""

from collections.abc import Iterable, Mapping
from typing import Any

import requests

from redi.api import query as query_api
from redi.api.exceptions import ProjectNotFoundException
from redi.api.query import Query
from redi.service.project_service import list_projects, resolve_project_id


def list_queries(all_pages: bool = False) -> list[Query]:
    """参照できるカスタムクエリを取得する。

    既定では Redmine の一覧 API の既定件数で打ち切られる。
    取りこぼせない用途では all_pages を指定する。
    """
    return query_api.fetch_queries(all_pages=all_pages)


def list_queries_for_project(project_id: str | None) -> list[Query]:
    """指定プロジェクトで使えるクエリ (プロジェクト固有 + グローバル) を返す。

    Redmine のクエリは `project_id` を持つプロジェクト固有のものと、それが
    `null` のグローバルなものが混ざる。他プロジェクトのクエリを渡しても
    絞り込めないので選択肢から外す。`project_id` が None ならグローバルのみを返す。

    クエリが持つ `project_id` は数値なので、identifier で指定されている場合は
    数値 id へ解決してから突き合わせる (config の `default_project_id` には
    identifier も書けるため、解決しないとプロジェクト固有のクエリを取りこぼす)。
    """
    owner_id = _resolve_owner_id(project_id)
    queries = []
    for query in list_queries(all_pages=True):
        owner = query["project_id"]
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


def resolve_query_project_names(
    queries: Iterable[Mapping[str, Any]],
) -> dict[int, str]:
    """クエリが参照しているプロジェクト id を名前に解決する。

    `/queries.json` は数値 id しか返さないため `/projects.json` を別に引く。
    プロジェクト指定のクエリが 1 件も無ければ API は呼ばない。

    参照している id を 1 件ずつ引けば転送量は減るが、リクエスト数がクエリの
    参照先の数だけ増える。1 リクエストで済む全件取得を選んでいる。

    一覧表示のための補足情報でしかないので、プロジェクト取得が失敗しても
    例外にはせず空の対応表を返す (呼び出し元が id のまま表示できる)。
    """
    wanted = {
        query["project_id"] for query in queries if query["project_id"] is not None
    }
    if not wanted:
        return {}
    try:
        projects = list_projects(all_pages=True)
    except requests.exceptions.RequestException:
        return {}
    return {
        project["id"]: project["name"]
        for project in projects
        if project["id"] in wanted
    }
