import json

import requests

from redi.client import client


def create_time_entry(
    issue_id: str | None = None,
    project_id: str | None = None,
    hours: float = 0,
    activity_id: str | None = None,
    spent_on: str | None = None,
    comments: str | None = None,
) -> None:
    if not issue_id and not project_id:
        print("issue_idまたはproject_idを指定してください")
        exit(1)
    data: dict = {"hours": hours}
    if issue_id:
        data["issue_id"] = issue_id
    if project_id:
        data["project_id"] = project_id
    if activity_id:
        data["activity_id"] = activity_id
    if spent_on:
        data["spent_on"] = spent_on
    if comments:
        data["comments"] = comments
    response = client.post("/time_entries.json", json={"time_entry": data})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("作業時間の登録に失敗しました")
        exit(1)
    created = response.json()["time_entry"]
    print(
        f"作業時間を登録しました: {created['id']} {created['hours']}h ({created['spent_on']})"
    )


def list_time_entries(
    project_id: str | None = None,
    user_id: str | None = None,
    full: bool = False,
) -> None:
    if project_id:
        path = f"/projects/{project_id}/time_entries.json"
    else:
        path = "/time_entries.json"
    params = {}
    if user_id:
        params["user_id"] = user_id
    response = client.get(path, params=params)
    response.raise_for_status()
    time_entries = response.json()["time_entries"]
    if full:
        print(json.dumps(time_entries, ensure_ascii=False))
    else:
        for te in time_entries:
            print(
                f"{te['id']} {te['hours']}h {te['activity']['name']} ({te['spent_on']})"
            )
