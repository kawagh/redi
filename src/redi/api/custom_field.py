import json

from redi import cache
from redi.client import client

CACHE_KEY = "custom_fields"


def fetch_custom_fields() -> list[dict] | None:
    cached = cache.load(CACHE_KEY)
    if cached is not None:
        return cached
    response = client.get("/custom_fields.json")
    if response.status_code == 403:
        # https://www.redmine.org/projects/redmine/wiki/Rest_CustomFields
        # https://www.redmine.org/issues/18875
        return
    response.raise_for_status()
    data = response.json()["custom_fields"]
    cache.save(CACHE_KEY, data)
    return data


def list_custom_fields(full: bool = False) -> None:
    custom_fields = fetch_custom_fields()
    if custom_fields is None:
        print("カスタムフィールドの取得には管理者権限が必要です")
        exit(1)
    if full:
        print(json.dumps(custom_fields, ensure_ascii=False))
    else:
        for cf in custom_fields:
            print(f"{cf['id']} {cf['name']}")


def fetch_project_issue_custom_field_ids(project_id: str) -> set[int]:
    """プロジェクトで有効なイシュー用カスタムフィールドのIDを取得する。"""
    response = client.get(
        f"/projects/{project_id}.json", params={"include": "issue_custom_fields"}
    )
    response.raise_for_status()
    project = response.json()["project"]

    return {cf["id"] for cf in project.get("issue_custom_fields") or []}


def filter_required_issue_custom_fields(
    custom_fields: list[dict],
    project_cf_ids: set[int],
    tracker_id: str | None,
) -> list[dict]:
    """
    入力必須・初期値なし・プロジェクト/トラッカーに該当する
    イシュー用カスタムフィールドを抽出する。
    """
    result = []
    for cf in custom_fields:
        if cf.get("customized_type") != "issue":
            continue
        if not cf.get("is_required"):
            continue
        if cf.get("default_value"):
            continue
        if cf["id"] not in project_cf_ids:
            continue
        trackers = cf.get("trackers") or []
        if trackers and tracker_id is not None:
            tracker_ids = {str(t["id"]) for t in trackers}
            if str(tracker_id) not in tracker_ids:
                continue
        result.append(cf)
    return result
