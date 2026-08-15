from __future__ import annotations

import json
import sys
import webbrowser
from typing import NotRequired, TypedDict, cast

import requests

from redi import config
from redi.api.exceptions import print_http_error_body
from redi.api.types import IdName
from redi.client import RedmineClient, client
from redi.i18n import messages

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


def list_projects(full: bool = False) -> None:
    projects = fetch_projects()
    if full:
        print(json.dumps(projects, ensure_ascii=False))
    else:
        for project in projects:
            print(f"{project['id']} {project['name']}")


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


def sort_projects_by_id_desc(projects: list[Project]) -> list[Project]:
    return sorted(projects, key=lambda p: p["id"], reverse=True)


def resolve_project_id(value: str) -> str:
    if str(value).isdigit():
        return str(value)
    projects = fetch_projects()
    for p in projects:
        if p.get("identifier") == value or p.get("name") == value:
            return str(p["id"])
    print(messages.project_not_found.format(id=value))
    sys.exit(1)


def fetch_project(project_id: str, include: str = "") -> Project:
    params: dict = {}
    if include:
        params["include"] = include
    response = client.get(f"/projects/{project_id}.json", params=params)
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    response.raise_for_status()
    return cast("Project", response.json()["project"])


def create_project(
    name: str,
    identifier: str,
    description: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    tracker_ids: list[int] | None = None,
) -> None:
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
    try:
        response = client.post("/projects.json", json={"project": data})
        response.raise_for_status()
        project = response.json()["project"]
        print(f"{project['id']} {project['name']} ({project['identifier']})")
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        sys.exit(1)


def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    is_public: bool | None = None,
    parent_id: str | None = None,
    tracker_ids: list[int] | None = None,
) -> None:
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
    if len(data) == 0:
        print(messages.update_canceled)
        sys.exit()
    response = client.put(f"/projects/{project_id}.json", json={"project": data})
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.project_update_failed)
        sys.exit(1)
    print(messages.project_updated.format(id=project_id))


def archive_project(project_id: str) -> None:
    response = client.put(f"/projects/{project_id}/archive.json")
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.project_archive_failed)
        sys.exit(1)
    print(messages.project_archived.format(id=project_id))


def unarchive_project(project_id: str) -> None:
    response = client.put(f"/projects/{project_id}/unarchive.json")
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.project_unarchive_failed)
        sys.exit(1)
    print(messages.project_unarchived.format(id=project_id))


def delete_project(project_id: str) -> None:
    response = client.delete(f"/projects/{project_id}.json")
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(e)
        print_http_error_body(e)
        print(messages.project_delete_failed)
        sys.exit(1)
    print(messages.project_deleted.format(id=project_id))


def read_project(
    project_id: str, include: str = "", full: bool = False, web: bool = False
) -> None:
    if web:
        url = f"{config.redmine_url}/projects/{project_id}"
        print(url)
        webbrowser.open(url)
        return
    params: dict = {}
    if include:
        params["include"] = include
    response = client.get(f"/projects/{project_id}.json", params=params)
    if response.status_code == 404:
        print(messages.project_not_found.format(id=project_id))
        sys.exit(1)
    response.raise_for_status()
    project = cast("Project", response.json()["project"])
    if full:
        print(json.dumps(project, ensure_ascii=False))
        return

    lines = []
    lines.append(f"{project['id']} {project['name']} ({project['identifier']})")
    description = project.get("description")
    if description:
        lines.append("")
        lines.append(description)
    parent = project.get("parent")
    if parent:
        lines.append("")
        lines.append(
            messages.label_parent_project.format(
                id=parent.get("id"), name=parent.get("name", "")
            )
        )
    trackers = project.get("trackers") or []
    if trackers:
        lines.append("")
        lines.append(messages.label_trackers_header)
        for t in trackers:
            lines.append(f"  {t['id']} {t['name']}")
    issue_categories = project.get("issue_categories") or []
    if issue_categories:
        lines.append("")
        lines.append(messages.label_issue_categories_header)
        for c in issue_categories:
            lines.append(f"  {c['id']} {c['name']}")
    enabled_modules = project.get("enabled_modules") or []
    if enabled_modules:
        lines.append("")
        lines.append(messages.label_enabled_modules_header)
        for m in enabled_modules:
            lines.append(f"  {m.get('name')}")
    print("\n".join(lines))
