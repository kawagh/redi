from __future__ import annotations

from typing import NotRequired, TypedDict, cast

from redi.api.exceptions import RedmineValidationException
from redi.api.types import IdName
from redi.client import client


class IssueCategory(TypedDict):
    """redmine issue category

    GET /projects/{id}/issue_categories.json / GET /issue_categories/{id}.json を
    実行して確認できたフィールドを記載。
    """

    id: int
    name: str
    project: IdName
    # デフォルト担当者が設定されている場合のみ存在
    assigned_to: NotRequired[IdName]


class IssueCategoryNotFoundException(Exception):
    """対象のイシューカテゴリが存在しないときに送出する例外。"""

    def __init__(self, category_id: str) -> None:
        super().__init__(category_id)
        self.category_id = category_id


def fetch_issue_categories(project_id: str) -> list[IssueCategory]:
    response = client.get(f"/projects/{project_id}/issue_categories.json")
    response.raise_for_status()
    return cast("list[IssueCategory]", response.json()["issue_categories"])


def fetch_issue_category(category_id: str) -> IssueCategory:
    """イシューカテゴリを取得する

    Raises:
        IssueCategoryNotFoundException: 対象カテゴリが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.get(f"/issue_categories/{category_id}.json")
    if response.status_code == 404:
        raise IssueCategoryNotFoundException(category_id)
    response.raise_for_status()
    return cast("IssueCategory", response.json()["issue_category"])


def create_issue_category(
    project_id: str,
    name: str,
    assigned_to_id: int | None = None,
) -> IssueCategory:
    """イシューカテゴリを作成し、作成されたカテゴリを返す

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 422 以外の HTTP エラーが返った場合
    """
    data: dict = {"name": name}
    if assigned_to_id is not None:
        data["assigned_to_id"] = assigned_to_id
    response = client.post(
        f"/projects/{project_id}/issue_categories.json",
        json={"issue_category": data},
    )
    if response.status_code == 422:
        raise RedmineValidationException.from_response(
            "issue_category", "create", response
        )
    response.raise_for_status()
    return cast("IssueCategory", response.json()["issue_category"])


def update_issue_category(
    category_id: str,
    name: str | None = None,
    assigned_to_id: int | None = None,
) -> None:
    """イシューカテゴリを更新する

    Raises:
        IssueCategoryNotFoundException: 対象カテゴリが存在しない場合（HTTP 404）
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 404 / 422 以外の HTTP エラーが返った場合
    """
    data: dict = {}
    if name is not None:
        data["name"] = name
    if assigned_to_id is not None:
        data["assigned_to_id"] = assigned_to_id
    response = client.put(
        f"/issue_categories/{category_id}.json",
        json={"issue_category": data},
    )
    if response.status_code == 404:
        raise IssueCategoryNotFoundException(category_id)
    if response.status_code == 422:
        raise RedmineValidationException.from_response(
            "issue_category", "update", response
        )
    response.raise_for_status()


def delete_issue_category(category_id: str, reassign_to_id: int | None = None) -> None:
    """イシューカテゴリを削除する

    Args:
        reassign_to_id: 削除するカテゴリに紐づくイシューの付け替え先カテゴリID

    Raises:
        IssueCategoryNotFoundException: 対象カテゴリが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    params: dict = {}
    if reassign_to_id is not None:
        params["reassign_to_id"] = reassign_to_id
    response = client.delete(f"/issue_categories/{category_id}.json", params=params)
    if response.status_code == 404:
        raise IssueCategoryNotFoundException(category_id)
    response.raise_for_status()
