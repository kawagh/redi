from __future__ import annotations

from typing import NotRequired, TypedDict, cast

from redi.api.exceptions import ProjectNotFoundException, RedmineValidationException
from redi.api.types import IdName
from redi.client import RedmineClient, client

# Redmine の一覧 API が 1 リクエストで返せる上限
PROJECTS_PAGE_LIMIT = 100


class Project(TypedDict):
    """redmine Project

    GET /projects.json / GET /projects/{id}.json を実行して確認できたフィールドを記載。
    `parent` や `trackers` などは親プロジェクトの有無や include 指定により
    存在しない場合がある。
    """

    id: int
    name: str
    identifier: str
    description: str | None
    homepage: str
    status: int
    is_public: bool
    inherit_members: bool
    created_on: str
    updated_on: str
    # 親プロジェクトを持つ場合のみ存在
    parent: NotRequired[IdName]
    # include 指定時のみ存在
    trackers: NotRequired[list[IdName]]
    issue_categories: NotRequired[list[IdName]]
    time_entry_activities: NotRequired[list[IdName]]
    enabled_modules: NotRequired[list[IdName]]


def fetch_projects(api_client: RedmineClient | None = None) -> list[Project]:
    """アクセスできるプロジェクトを全件返す。

    Redmine の一覧 API は limit 未指定だと既定件数しか返さないため、
    `total_count` を見て全件揃うまで offset を進める。

    `api_client` は config 未確定の `redi init` から、入力されたばかりの
    URL/API キーで呼ぶために受ける。省略時はグローバルの client を使う。
    """
    target = api_client or client
    projects: list[Project] = []
    offset = 0
    while True:
        response = target.get(
            "/projects.json", params={"limit": PROJECTS_PAGE_LIMIT, "offset": offset}
        )
        response.raise_for_status()
        data = response.json()
        page = cast("list[Project]", data.get("projects", []))
        projects.extend(page)
        total_count = data.get("total_count")
        if not page or total_count is None or len(projects) >= total_count:
            return projects
        offset += len(page)


def fetch_project(project_id: str, include: str = "") -> Project:
    """プロジェクトを取得する

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    params: dict = {}
    if include:
        params["include"] = include
    response = client.get(f"/projects/{project_id}.json", params=params)
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()
    return cast("Project", response.json()["project"])


def create_project(
    name: str,
    identifier: str,
    description: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    tracker_ids: list[int] | None = None,
) -> Project:
    """プロジェクトを作成し、作成されたプロジェクトを返す

    Raises:
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 422 以外の HTTP エラーが返った場合
    """
    data: dict = {
        "name": name,
        "identifier": identifier,
    }
    if description is not None:
        data["description"] = description
    if is_public is not None:
        data["is_public"] = is_public
    if parent_id is not None:
        data["parent_id"] = parent_id
    if tracker_ids is not None:
        data["tracker_ids"] = tracker_ids
    response = client.post("/projects.json", json={"project": data})
    if response.status_code == 422:
        raise RedmineValidationException.from_response("project", "create", response)
    response.raise_for_status()
    return cast("Project", response.json()["project"])


def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    tracker_ids: list[int] | None = None,
) -> None:
    """プロジェクトを更新する

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        RedmineValidationException: Redmine がバリデーションエラー (HTTP 422) を返した場合
        requests.exceptions.HTTPError: 404 / 422 以外の HTTP エラーが返った場合
    """
    data: dict = {}
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description
    if is_public is not None:
        data["is_public"] = is_public
    if parent_id is not None:
        data["parent_id"] = parent_id
    if tracker_ids is not None:
        data["tracker_ids"] = tracker_ids
    response = client.put(f"/projects/{project_id}.json", json={"project": data})
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    if response.status_code == 422:
        raise RedmineValidationException.from_response("project", "update", response)
    response.raise_for_status()


def archive_project(project_id: str) -> None:
    """プロジェクトをアーカイブする

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.put(f"/projects/{project_id}/archive.json")
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()


def unarchive_project(project_id: str) -> None:
    """プロジェクトのアーカイブを解除する

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.put(f"/projects/{project_id}/unarchive.json")
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()


def delete_project(project_id: str) -> None:
    """プロジェクトを削除する

    Raises:
        ProjectNotFoundException: 対象プロジェクトが存在しない場合（HTTP 404）
        requests.exceptions.HTTPError: 404 以外の HTTP エラーが返った場合
    """
    response = client.delete(f"/projects/{project_id}.json")
    if response.status_code == 404:
        raise ProjectNotFoundException(project_id)
    response.raise_for_status()
