import json

from redi.client import client
from redi.i18n import messages


# https://www.redmine.org/projects/redmine/wiki/Rest_Search
SEARCH_SCOPES = ("all", "my_projects", "bookmarks", "subprojects")
SEARCH_TYPES = (
    "issues",
    "news",
    "documents",
    "changesets",
    "wiki_pages",
    "messages",
    "projects",
)
SEARCH_ATTACHMENTS = ("0", "1", "only")


# Optinal parameters
def search(
    query: str,
    limit: int | None = None,
    offset: int | None = None,
    scope: str | None = None,
    all_words: bool | None = None,
    titles_only: bool = False,
    open_issues: bool = False,
    attachments: str | None = None,
    types: list[str] | None = None,
    full: bool = False,
) -> None:
    params: dict = {"q": query}
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    if scope is not None:
        params["scope"] = scope
    if all_words is not None:
        # Redmine は値の有無で真偽を判定するため、無効化するには空値を渡す
        params["all_words"] = "1" if all_words else ""
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
    data = response.json()
    results = data.get("results", [])
    if full:
        print(json.dumps(data, ensure_ascii=False))
        return
    if not results:
        print(messages.no_search_results)
        return
    for r in results:
        print(f"[{r.get('type', '')}] {r.get('title', '')} {r.get('url', '')}")
