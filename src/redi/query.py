import json

from redi.client import client


def list_queries(full: bool = False) -> None:
    response = client.get("/queries.json")
    response.raise_for_status()
    queries = response.json()["queries"]
    if full:
        print(json.dumps(queries, ensure_ascii=False))
    else:
        for q in queries:
            print(f"{q['id']} {q['name']}")
