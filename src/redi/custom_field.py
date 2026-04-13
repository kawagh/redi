import json

from redi.client import client


def list_custom_fields(full: bool = False) -> None:
    response = client.get("/custom_fields.json")
    if response.status_code == 403:
        # https://www.redmine.org/projects/redmine/wiki/Rest_CustomFields
        # https://www.redmine.org/issues/18875
        print("カスタムフィールドの取得には管理者権限が必要です")
        exit()
    response.raise_for_status()
    custom_fields = response.json()["custom_fields"]
    if full:
        print(json.dumps(custom_fields, ensure_ascii=False))
    else:
        for cf in custom_fields:
            print(f"{cf['id']} {cf['name']}")
