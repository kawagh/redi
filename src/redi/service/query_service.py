"""カスタムクエリのサービス層。

`/queries.json` はクエリのフィルタ内容を返さず、素性が分かるのは
`is_public` と `project_id` だけになる。その `project_id` は数値 id なので、
名前で見せるためのプロジェクト解決をここに置く。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import requests

from redi.api import project as project_api
from redi.api.query import fetch_queries


def list_queries() -> list[dict]:
    """アクセスできるカスタムクエリを全件取得する。"""
    return fetch_queries()


def resolve_query_project_names(
    queries: Iterable[Mapping[str, Any]],
) -> dict[int, str]:
    """クエリが参照しているプロジェクト id を名前に解決する。

    `/queries.json` は数値 id しか返さないため `/projects.json` を別に引く。
    プロジェクト指定のクエリが 1 件も無ければ API は呼ばない。

    一覧表示のための補足情報でしかないので、プロジェクト取得が失敗しても
    例外にはせず空の対応表を返す (呼び出し元が id のまま表示できる)。
    """
    wanted = {
        query["project_id"] for query in queries if query.get("project_id") is not None
    }
    if not wanted:
        return {}
    try:
        projects = project_api.fetch_projects()
    except requests.exceptions.RequestException:
        return {}
    return {
        project["id"]: project["name"]
        for project in projects
        if project["id"] in wanted
    }
