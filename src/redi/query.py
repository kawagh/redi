import json

import requests

from redi.config import redmine_api_key, redmine_url


def list_queries(full: bool = False) -> None:
    response = requests.get(
        f"{redmine_url}/queries.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    response.raise_for_status()
    queries = response.json()["queries"]
    if full:
        print(json.dumps(queries, ensure_ascii=False))
    else:
        for q in queries:
            print(f"{q['id']} {q['name']}")
