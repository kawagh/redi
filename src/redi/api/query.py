from typing import TypedDict, cast

from redi.client import client

# `/queries.json` は limit 未指定だと既定 25 件しか返さないため明示する。
QUERIES_PAGE_LIMIT = 100


class Query(TypedDict):
    """`queries[]` の要素。

    4 つとも常に返る (Redmine 6.1 / 7.0 で実測)。グローバルクエリは
    `project_id` のキーが欠けるのではなく `null` が入る。
    """

    id: int
    name: str
    is_public: bool
    project_id: int | None


def fetch_queries() -> list[Query]:
    """参照できるカスタムクエリを全件返す。

    Redmine の一覧 API は既定件数で打ち切られるため、`total_count` を見て
    全件揃うまで offset を進める。
    """
    queries: list[Query] = []
    offset = 0
    while True:
        response = client.get(
            "/queries.json", params={"limit": QUERIES_PAGE_LIMIT, "offset": offset}
        )
        response.raise_for_status()
        data = response.json()
        page = cast("list[Query]", data.get("queries", []))
        queries.extend(page)
        total_count = data.get("total_count")
        if not page or total_count is None or len(queries) >= total_count:
            return queries
        offset += len(page)
