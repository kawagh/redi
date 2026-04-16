import json

from redi import cache
from redi.client import client

CACHE_KEY = "custom_fields"


def fetch_custom_fields() -> list[dict]:
    cached = cache.load(CACHE_KEY)
    if cached is not None:
        return cached
    response = client.get("/custom_fields.json")
    if response.status_code == 403:
        # https://www.redmine.org/projects/redmine/wiki/Rest_CustomFields
        # https://www.redmine.org/issues/18875
        print("カスタムフィールドの取得には管理者権限が必要です")
        exit()
    response.raise_for_status()
    data = response.json()["custom_fields"]
    cache.save(CACHE_KEY, data)
    return data


def list_custom_fields(full: bool = False) -> None:
    custom_fields = fetch_custom_fields()
    if full:
        print(json.dumps(custom_fields, ensure_ascii=False))
    else:
        for cf in custom_fields:
            print(f"{cf['id']} {cf['name']}")
