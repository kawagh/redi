import json

import requests

from redi.config import redmine_api_key, redmine_url


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
    response = requests.get(
        f"{redmine_url}/search.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
        params=params,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    if full:
        print(json.dumps(data, ensure_ascii=False))
        return
    if not results:
        print("検索結果が見つかりませんでした")
        return
    for r in results:
        print(f"[{r.get('type', '')}] {r.get('title', '')} {r.get('url', '')}")
