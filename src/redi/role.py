import json

import requests

from redi.config import redmine_api_key, redmine_url


def list_roles(full: bool = False) -> None:
    response = requests.get(
        f"{redmine_url}/roles.json",
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    response.raise_for_status()
    roles = response.json()["roles"]
    if full:
        print(json.dumps(roles, ensure_ascii=False))
    else:
        for role in roles:
            print(f"{role['id']} {role['name']}")
