from redi.client import client


def fetch_queries() -> list[dict]:
    response = client.get("/queries.json")
    response.raise_for_status()
    return response.json()["queries"]
