import json

from redi.client import client
from redi.i18n import messages


# https://www.redmine.org/projects/redmine/wiki/Rest_Search
# Optinal parameters
def search(
    query: str,
    limit: int | None = None,
    offset: int | None = None,
    full: bool = False,
) -> None:
    params: dict = {"q": query}
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
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
