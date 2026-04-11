import json

import requests

from redi.config import redmine_api_key, redmine_url


def list_custom_fields(full: bool = False) -> None:
    response = requests.get(
        f"{redmine_url}/custom_fields.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    response.raise_for_status()
    custom_fields = response.json()["custom_fields"]
    if full:
        print(json.dumps(custom_fields, ensure_ascii=False))
    else:
        for cf in custom_fields:
            print(f"{cf['id']} {cf['name']}")
