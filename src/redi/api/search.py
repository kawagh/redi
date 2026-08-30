from typing import Literal, TypedDict, cast, get_args

from redi.client import client

# https://www.redmine.org/projects/redmine/wiki/Rest_Search
SearchScope = Literal["all", "my_projects", "bookmarks", "subprojects"]
SearchType = Literal[
    "issues",
    "news",
    "documents",
    "changesets",
    "wiki_pages",
    "messages",
    "projects",
]
SearchAttachments = Literal["0", "1", "only"]

# argparse の choices や検証に使うため、Literal から実行時の値を導出する
SEARCH_SCOPES: tuple[SearchScope, ...] = get_args(SearchScope)
SEARCH_TYPES: tuple[SearchType, ...] = get_args(SearchType)
SEARCH_ATTACHMENTS: tuple[SearchAttachments, ...] = get_args(SearchAttachments)


class SearchResult(TypedDict):
    """検索結果1件。イシューでも wiki でも同じ形で返る。

    `title` は Redmine 側で組み立て済みの文字列 (例: `サポート #223 (新規): 件名`) で、
    トラッカーやステータスは構造化されていない。
    """

    id: int
    title: str
    type: str
    url: str
    description: str
    datetime: str


class SearchPageResponse(TypedDict):
    results: list[SearchResult]
    total_count: int
    offset: int
    limit: int


# Optinal parameters
def search(
    query: str,
    limit: int | None = None,
    offset: int | None = None,
    project_id: str | None = None,
    scope: SearchScope | None = None,
    all_words: bool = True,
    titles_only: bool = False,
    open_issues: bool = False,
    attachments: SearchAttachments | None = None,
    types: list[SearchType] | None = None,
) -> SearchPageResponse:
    params: dict = {"q": query}
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    if project_id is not None:
        # ルートが (projects/:id)/search のため、絞り込みのパラメータ名は id になる
        params["id"] = project_id
    if scope is not None:
        params["scope"] = scope
    if not all_words:
        # Redmine は値の有無で真偽を判定するため、無効化するには空値を渡す
        params["all_words"] = ""
    if titles_only:
        params["titles_only"] = "1"
    if open_issues:
        params["open_issues"] = "1"
    if attachments is not None:
        params["attachments"] = attachments
    for search_type in types or []:
        params[search_type] = "1"
    response = client.get("/search.json", params=params)
    response.raise_for_status()
    return cast(SearchPageResponse, response.json())
