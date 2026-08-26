from typing import Literal, NotRequired, TypedDict, cast

from redi import cache
from redi.api.types import IdName
from redi.client import client

CACHE_KEY = "custom_fields"


class CustomField(TypedDict):
    id: int
    name: str
    description: str
    customized_type: str  # ex. issue
    field_format: Literal[
        # キーバリューリスト
        "enumeration",
        # テキスト
        "string",
        "version",
        "attachment",
        "user",
        "list",
        "link",
        "float",
        "int",
        "bool",
        "date",
        "progressbar",
        # 長いテキスト
        "text",
    ]
    regexp: str
    min_length: int | None
    max_length: int | None
    is_required: bool
    # Redmine 7.0 以降で返る
    is_for_all: NotRequired[bool]
    is_filter: bool
    searchable: bool
    multiple: bool
    default_value: str | None
    visible: bool
    editable: bool
    possible_values: NotRequired[list[dict]]
    # Redmine 7.0 以降で返る。is_for_all が false のとき対象プロジェクトが入る
    projects: NotRequired[list[IdName]]
    trackers: list[dict]
    roles: list[dict]


def fetch_custom_fields(refresh: bool = False) -> list[CustomField] | None:
    """カスタムフィールドの一覧を返す。管理者権限が無い場合は None を返す。

    refresh=True ならキャッシュを読まず取り直す。
    """
    cached = None if refresh else cache.load(CACHE_KEY)
    if cached is not None:
        return cast(list[CustomField], cached)
    response = client.get("/custom_fields.json")
    if response.status_code == 403:
        # https://www.redmine.org/projects/redmine/wiki/Rest_CustomFields
        # https://www.redmine.org/issues/18875
        return
    response.raise_for_status()
    data = response.json()["custom_fields"]
    cache.save(CACHE_KEY, data)
    return cast(list[CustomField], data)


def fetch_project_issue_custom_field_ids(project_id: str) -> set[int]:
    """プロジェクトで有効なイシュー用カスタムフィールドのIDを取得する。"""
    response = client.get(
        f"/projects/{project_id}.json", params={"include": "issue_custom_fields"}
    )
    response.raise_for_status()
    project = response.json()["project"]

    return {cf["id"] for cf in project.get("issue_custom_fields") or []}


def filter_required_issue_custom_fields(
    custom_fields: list[CustomField],
    project_cf_ids: set[int],
    tracker_id: str | None,
) -> list[CustomField]:
    """
    入力必須・プロジェクト/トラッカーに該当するイシュー用カスタムフィールドを抽出する。
    """
    result = []
    for cf in custom_fields:
        if cf.get("customized_type") != "issue":
            continue
        if not cf.get("is_required"):
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


def filter_optional_issue_custom_fields(
    custom_fields: list[CustomField],
    project_cf_ids: set[int],
    tracker_id: str | None,
) -> list[CustomField]:
    """
    入力任意・プロジェクト/トラッカーに該当するイシュー用カスタムフィールドを抽出する。
    """
    result = []
    for cf in custom_fields:
        if cf.get("customized_type") != "issue":
            continue
        if cf.get("is_required"):
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
