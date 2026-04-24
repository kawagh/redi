import json

import requests

from redi.api.project import resolve_project_id
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
    # time_entries は他の API と異なり project_id に slug を受け付けず整数のみ許容
    # https://www.redmine.org/projects/redmine/wiki/Rest_TimeEntries
    if project_id is not None:
        project_id = resolve_project_id(project_id)
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


def fetch_time_entry(time_entry_id: str) -> dict:
    response = client.get(f"/time_entries/{time_entry_id}.json")
    if response.status_code == 404:
        print(f"作業時間が見つかりません: {time_entry_id}")
        exit(1)
    response.raise_for_status()
    return response.json()["time_entry"]


def read_time_entry(time_entry_id: str, full: bool = False) -> None:
    te = fetch_time_entry(time_entry_id)
    if full:
        print(json.dumps(te, ensure_ascii=False))
        return
    lines = [
        f"{te['id']} {te['hours']}h {te['activity']['name']} ({te['spent_on']})",
        f"  プロジェクト: {te['project']['name']} (id={te['project']['id']})",
        f"  ユーザー: {te['user']['name']} (id={te['user']['id']})",
    ]
    issue = te.get("issue")
    if issue:
        lines.append(f"  イシュー: #{issue['id']}")
    comments = te.get("comments")
    if comments:
        lines.append(f"  コメント: {comments}")
    print("\n".join(lines))


def update_time_entry(
    time_entry_id: str,
    hours: float | None = None,
    issue_id: str | None = None,
    project_id: str | None = None,
    activity_id: str | None = None,
    spent_on: str | None = None,
    comments: str | None = None,
) -> None:
    # time_entries は他の API と異なり project_id に slug を受け付けず整数のみ許容
    # https://www.redmine.org/projects/redmine/wiki/Rest_TimeEntries
    if project_id is not None:
        project_id = resolve_project_id(project_id)
    data: dict = {}
    if hours is not None:
        data["hours"] = hours
    if issue_id:
        data["issue_id"] = issue_id
    if project_id:
        data["project_id"] = project_id
    if activity_id:
        data["activity_id"] = activity_id
    if spent_on:
        data["spent_on"] = spent_on
    if comments is not None:
        data["comments"] = comments
    if not data:
        print("更新内容がないので更新をキャンセルしました")
        exit(1)
    response = client.put(
        f"/time_entries/{time_entry_id}.json", json={"time_entry": data}
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("作業時間の更新に失敗しました")
        exit(1)
    print(f"作業時間を更新しました: {time_entry_id}")


def delete_time_entry(time_entry_id: str) -> None:
    response = client.delete(f"/time_entries/{time_entry_id}.json")
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print(e.response.text)
        print("作業時間の削除に失敗しました")
        exit(1)
    print(f"作業時間を削除しました: {time_entry_id}")
