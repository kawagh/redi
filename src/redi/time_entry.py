import json

import requests

from redi.config import redmine_api_key, redmine_url


def list_time_entries(project_id: str | None = None, full: bool = False) -> None:
    if project_id:
        url = f"{redmine_url}/projects/{project_id}/time_entries.json"
    else:
        url = f"{redmine_url}/time_entries.json"
    response = requests.get(
        url,
        headers={"X-Redmine-API-Key": redmine_api_key},
    )
    response.raise_for_status()
    time_entries = response.json()["time_entries"]
    if full:
        print(json.dumps(time_entries, ensure_ascii=False))
    else:
        for te in time_entries:
            print(f"{te['id']} {te['hours']}h {te['activity']['name']} ({te['spent_on']})")
